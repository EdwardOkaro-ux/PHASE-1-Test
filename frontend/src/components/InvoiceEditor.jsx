import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Textarea } from '../components/ui/textarea';
import { Switch } from '../components/ui/switch';
import { Checkbox } from '../components/ui/checkbox';
import { ScrollArea } from '../components/ui/scroll-area';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '../components/ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '../components/ui/alert-dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { toast } from 'sonner';
import { 
  Plus, FileText, Send, Trash2, Download, CheckCircle, Clock, AlertCircle,
  X, DollarSign, Receipt, Loader2, AlertTriangle, Banknote, Building2, 
  Smartphone, CreditCard, Save
} from 'lucide-react';
import { format } from 'date-fns';
import { cn } from '../lib/utils';
import { useNavigate, useLocation } from 'react-router-dom';

const API = `${window.location.origin}/api`;

// Status config
const statusConfig = {
  draft: { bg: 'bg-gray-100', text: 'text-gray-700', label: 'Draft' },
  sent: { bg: 'bg-[#E8DC88]', text: 'text-[#3C3F42]', label: 'Sent' },
  paid: { bg: 'bg-green-100', text: 'text-green-700', label: 'Paid' },
  overdue: { bg: 'bg-red-100', text: 'text-red-700', label: 'Overdue' },
  partial: { bg: 'bg-yellow-100', text: 'text-yellow-700', label: 'Partial' }
};

// Default exchange rate (will be fetched from settings)
const DEFAULT_KES_RATE = 6.67;

const paymentMethodConfig = {
  cash: { icon: Banknote, label: 'Cash' },
  bank_transfer: { icon: Building2, label: 'Bank Transfer' },
  mobile_money: { icon: Smartphone, label: 'Mobile Money' },
  other: { icon: CreditCard, label: 'Other' }
};

export function InvoiceEditor() {
  const navigate = useNavigate();
  const location = useLocation();
  
  // Exchange rates from settings
  const [exchangeRates, setExchangeRates] = useState({ KES: DEFAULT_KES_RATE });
  
  // Data states
  const [invoices, setInvoices] = useState([]);
  const [trips, setTrips] = useState([]);
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Filter states
  const [tripFilter, setTripFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  
  // Selected invoice state
  const [selectedInvoiceId, setSelectedInvoiceId] = useState(null);
  const [invoiceData, setInvoiceData] = useState(null);
  const [invoiceLoading, setInvoiceLoading] = useState(false);
  
  // Create/Edit mode
  const [isCreating, setIsCreating] = useState(false);
  const [formData, setFormData] = useState({
    client_id: '',
    trip_id: '',
    display_currency: 'ZAR',
    issue_date: new Date().toISOString().split('T')[0],
    due_date: '',
    payment_terms: '',
    payment_terms_custom: ''
  });
  
  // Initial form data for dirty checking
  const [initialFormData, setInitialFormData] = useState(null);
  const [initialLineItems, setInitialLineItems] = useState([]);
  const [initialAdjustments, setInitialAdjustments] = useState([]);
  
  // Unsaved changes warning
  const [showUnsavedWarning, setShowUnsavedWarning] = useState(false);
  const [pendingNavigation, setPendingNavigation] = useState(null);
  
  // Line items (stored in ZAR)
  const [lineItems, setLineItems] = useState([]);
  // Adjustments (stored in ZAR)
  const [adjustments, setAdjustments] = useState([]);
  // Client default rate
  const [clientDefaultRate, setClientDefaultRate] = useState(0);
  
  // Selected line items for batch operations
  const [selectedLineItems, setSelectedLineItems] = useState(new Set());
  const [batchRateDialogOpen, setBatchRateDialogOpen] = useState(false);
  const [batchRate, setBatchRate] = useState('');
  
  // Reverse calculator
  const [targetTotal, setTargetTotal] = useState('');
  const [calculatedRate, setCalculatedRate] = useState(null);
  
  // Dialog states
  const [paymentDialogOpen, setPaymentDialogOpen] = useState(false);
  const [parcelsDialogOpen, setParcelsDialogOpen] = useState(false);
  const [availableParcels, setAvailableParcels] = useState([]);
  const [selectedParcels, setSelectedParcels] = useState(new Set());
  
  // Warehouse parcels dialog
  const [warehouseDialogOpen, setWarehouseDialogOpen] = useState(false);
  const [warehouseParcels, setWarehouseParcels] = useState([]);
  const [warehouseFilter, setWarehouseFilter] = useState('all');
  const [warehouseClientFilter, setWarehouseClientFilter] = useState('all');
  const [warehouseSearch, setWarehouseSearch] = useState('');
  const [selectedWarehouseParcels, setSelectedWarehouseParcels] = useState(new Set());
  const [loadingWarehouseParcels, setLoadingWarehouseParcels] = useState(false);
  
  // Parcel reassignment
  const [reassignWarning, setReassignWarning] = useState(null);
  const [isProcessingParcels, setIsProcessingParcels] = useState(false);
  
  // Payment form
  const [paymentForm, setPaymentForm] = useState({
    amount: '',
    payment_date: new Date().toISOString().split('T')[0],
    payment_method: 'bank_transfer',
    reference: '',
    notes: ''
  });
  
  const [submitting, setSubmitting] = useState(false);

  // Payment terms options
  const paymentTermsOptions = [
    { value: 'full_on_receipt', label: 'Full payment due on receipt' },
    { value: '50_50', label: '50% upfront, 50% on delivery' },
    { value: '30_70', label: '30% upfront, 70% on delivery' },
    { value: 'net_30', label: 'Net 30 days' },
    { value: 'custom', label: 'Custom terms' }
  ];

  // Fetch exchange rates from settings
  useEffect(() => {
    const fetchExchangeRates = async () => {
      try {
        const response = await axios.get(`${API}/settings/currencies`, { withCredentials: true });
        if (response.data?.currencies) {
          const rates = {};
          response.data.currencies.forEach(c => {
            rates[c.code] = c.exchange_rate;
          });
          setExchangeRates(rates);
        }
      } catch (error) {
        console.error('Failed to fetch exchange rates:', error);
      }
    };
    fetchExchangeRates();
  }, []);

  // Get current exchange rate for KES
  const KES_RATE = exchangeRates.KES || DEFAULT_KES_RATE;

  // Currency helpers
  const toDisplayCurrency = useCallback((zarAmount) => {
    return formData.display_currency === 'KES' ? zarAmount * KES_RATE : zarAmount;
  }, [formData.display_currency, KES_RATE]);

  const toZAR = useCallback((amount, fromCurrency) => {
    return fromCurrency === 'KES' ? amount / KES_RATE : amount;
  }, [KES_RATE]);

  const formatCurrency = useCallback((zarAmount) => {
    const displayAmount = toDisplayCurrency(zarAmount);
    const symbol = formData.display_currency === 'KES' ? 'KES ' : 'R ';
    return symbol + (displayAmount || 0).toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }, [toDisplayCurrency, formData.display_currency]);

  // Check if form has unsaved changes
  const hasUnsavedChanges = useMemo(() => {
    // Don't show warning during parcel operations
    if (isProcessingParcels || submitting) return false;
    if (!initialFormData) return false;
    
    // Check form data
    const formChanged = JSON.stringify(formData) !== JSON.stringify(initialFormData);
    
    // Check line items (compare by relevant fields)
    const lineItemsChanged = JSON.stringify(lineItems.map(li => ({
      description: li.description,
      quantity: li.quantity,
      rate: li.rate,
      amount: li.amount
    }))) !== JSON.stringify(initialLineItems.map(li => ({
      description: li.description,
      quantity: li.quantity,
      rate: li.rate,
      amount: li.amount
    })));
    
    // Check adjustments
    const adjustmentsChanged = JSON.stringify(adjustments) !== JSON.stringify(initialAdjustments);
    
    return formChanged || lineItemsChanged || adjustmentsChanged;
  }, [formData, initialFormData, lineItems, initialLineItems, adjustments, initialAdjustments]);

  // Browser beforeunload warning
  useEffect(() => {
    const handleBeforeUnload = (e) => {
      if (hasUnsavedChanges) {
        e.preventDefault();
        e.returnValue = '';
      }
    };
    
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [hasUnsavedChanges]);

  // Calculate totals with validation
  const totals = useMemo(() => {
    const subtotal = lineItems.reduce((sum, item) => sum + (parseFloat(item.amount) || 0), 0);
    const adjustmentTotal = adjustments.reduce((sum, adj) => {
      const amount = parseFloat(adj.amount) || 0;
      return sum + (adj.is_addition ? amount : -amount);
    }, 0);
    const totalQty = lineItems.reduce((sum, item) => sum + (parseInt(item.quantity) || 0), 0);
    return { subtotal, adjustmentTotal, total: subtotal + adjustmentTotal, totalQty };
  }, [lineItems, adjustments]);

  // Format weight with 2 decimals
  const formatWeight = (weight) => {
    if (weight === null || weight === undefined) return '-';
    return parseFloat(weight).toFixed(2) + ' kg';
  };

  // Get display values for qty and weight, handling legacy data
  // Legacy data: quantity contains weight, weight is null
  const getItemDisplayValues = (item) => {
    const qty = item.quantity;
    const weight = item.weight;
    
    // If weight is present, use as-is
    if (weight !== null && weight !== undefined) {
      return {
        qty: qty || 1,
        weight: weight,
        isLegacy: false
      };
    }
    
    // Legacy case: quantity contains weight (decimals or > 10)
    if (qty !== null && qty !== undefined) {
      const qtyNum = parseFloat(qty);
      if (qtyNum !== Math.floor(qtyNum) || qtyNum > 10) {
        // This is likely a weight stored in quantity
        return {
          qty: 1,
          weight: qtyNum,
          isLegacy: true
        };
      }
    }
    
    return {
      qty: qty || 1,
      weight: null,
      isLegacy: false
    };
  };

  // Format dimension with 1 decimal
  const formatDimension = (dim) => {
    if (dim === null || dim === undefined) return '-';
    return parseFloat(dim).toFixed(1);
  };

  // Format L×W×H dimensions with 1 decimal
  const formatDimensions = (length, width, height) => {
    if (!length && !width && !height) return '-';
    const l = length ? parseFloat(length).toFixed(1) : '0';
    const w = width ? parseFloat(width).toFixed(1) : '0';
    const h = height ? parseFloat(height).toFixed(1) : '0';
    return `${l}×${w}×${h}`;
  };

  // Calculate volumetric weight: (L × W × H) / 5000
  const calculateVolumetricWeight = (length, width, height) => {
    if (!length || !width || !height) return null;
    const l = parseFloat(length) || 0;
    const w = parseFloat(width) || 0;
    const h = parseFloat(height) || 0;
    if (l === 0 || w === 0 || h === 0) return null;
    return (l * w * h) / 5000;
  };

  // Get shipping weight (max of actual and volumetric)
  const getShippingWeight = (actualWeight, volumetricWeight) => {
    const actual = parseFloat(actualWeight) || 0;
    const vol = parseFloat(volumetricWeight) || 0;
    return Math.max(actual, vol);
  };

  // Batch rate update for selected items
  const handleBatchRateUpdate = () => {
    if (!batchRate || selectedLineItems.size === 0) return;
    
    const newRate = parseFloat(batchRate);
    if (isNaN(newRate)) {
      toast.error('Invalid rate');
      return;
    }
    
    setLineItems(items => items.map(item => {
      if (selectedLineItems.has(item.id)) {
        const weight = parseFloat(item.weight) || parseFloat(item.quantity) || 0;
        return {
          ...item,
          rate: newRate,
          amount: weight * newRate
        };
      }
      return item;
    }));
    
    setBatchRateDialogOpen(false);
    setBatchRate('');
    setSelectedLineItems(new Set());
    toast.success(`Updated rate for ${selectedLineItems.size} items`);
  };

  // Calculate reverse rate
  const handleCalculateRate = () => {
    const target = parseFloat(targetTotal);
    if (isNaN(target) || target <= 0) {
      toast.error('Enter a valid target amount');
      return;
    }
    
    // Calculate total weight of selected items (or all items if none selected)
    const itemsToCalculate = selectedLineItems.size > 0 
      ? lineItems.filter(item => selectedLineItems.has(item.id))
      : lineItems;
    
    const totalWeight = itemsToCalculate.reduce((sum, item) => {
      return sum + (parseFloat(item.weight) || parseFloat(item.quantity) || 0);
    }, 0);
    
    if (totalWeight <= 0) {
      toast.error('No weight to calculate rate from');
      return;
    }
    
    const rate = target / totalWeight;
    setCalculatedRate(rate.toFixed(2));
    toast.success(`Rate needed: R ${rate.toFixed(2)} per kg`);
  };

  // Apply calculated rate
  const applyCalculatedRate = () => {
    if (!calculatedRate) return;
    setBatchRate(calculatedRate);
    setBatchRateDialogOpen(true);
  };

  // Toggle line item selection
  const toggleLineItemSelection = (itemId) => {
    setSelectedLineItems(prev => {
      const next = new Set(prev);
      if (next.has(itemId)) {
        next.delete(itemId);
      } else {
        next.add(itemId);
      }
      return next;
    });
  };

  // Toggle all line items
  const toggleAllLineItems = () => {
    if (selectedLineItems.size === lineItems.length) {
      setSelectedLineItems(new Set());
    } else {
      setSelectedLineItems(new Set(lineItems.map(item => item.id)));
    }
  };

  // Fetch data
  const fetchInvoices = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (tripFilter !== 'all') params.append('trip_id', tripFilter);
      if (statusFilter !== 'all') params.append('status', statusFilter);
      
      const response = await axios.get(`${API}/invoices-enhanced?${params}`, { withCredentials: true });
      setInvoices(response.data);
    } catch (error) {
      toast.error('Failed to fetch invoices');
    } finally {
      setLoading(false);
    }
  }, [tripFilter, statusFilter]);

  const fetchTripsAndClients = async () => {
    try {
      const [tripsRes, clientsRes] = await Promise.all([
        axios.get(`${API}/trips`, { withCredentials: true }),
        axios.get(`${API}/clients`, { withCredentials: true })
      ]);
      setTrips(tripsRes.data || []);
      setClients(clientsRes.data || []);
    } catch (error) {
      console.error('Failed to fetch trips/clients');
    }
  };

  const fetchClientRate = async (clientId) => {
    try {
      const response = await axios.get(`${API}/clients/${clientId}/rate`, { withCredentials: true });
      if (response.data?.rate_per_kg) {
        setClientDefaultRate(response.data.rate_per_kg);
        return response.data.rate_per_kg;
      }
    } catch (error) {
      console.error('Failed to fetch client rate');
    }
    setClientDefaultRate(0);
    return 0;
  };

  useEffect(() => {
    fetchInvoices();
    fetchTripsAndClients();
  }, [fetchInvoices]);

  // Invoice selection
  const selectInvoice = async (invoiceId) => {
    // Check for unsaved changes before switching
    if (hasUnsavedChanges) {
      setShowUnsavedWarning(true);
      setPendingNavigation({ type: 'selectInvoice', invoiceId });
      return;
    }
    
    await loadInvoice(invoiceId);
  };

  // Load invoice data
  const loadInvoice = async (invoiceId) => {
    setSelectedInvoiceId(invoiceId);
    setIsCreating(false);
    setInvoiceLoading(true);
    
    try {
      const response = await axios.get(`${API}/invoices/${invoiceId}`, { withCredentials: true });
      const inv = response.data;
      setInvoiceData(inv);
      
      const newFormData = {
        client_id: inv.client_id || '',
        trip_id: inv.trip_id || '',
        display_currency: inv.currency || 'ZAR',
        issue_date: inv.issue_date?.split('T')[0] || new Date().toISOString().split('T')[0],
        due_date: inv.due_date?.split('T')[0] || '',
        payment_terms: inv.payment_terms || '',
        payment_terms_custom: inv.payment_terms_custom || ''
      };
      
      setFormData(newFormData);
      setLineItems(inv.line_items || []);
      setAdjustments(inv.adjustments || []);
      
      // Store initial state for dirty checking
      setInitialFormData(newFormData);
      setInitialLineItems(inv.line_items || []);
      setInitialAdjustments(inv.adjustments || []);
      
      if (inv.client_id) fetchClientRate(inv.client_id);
    } catch (error) {
      toast.error('Failed to load invoice');
    } finally {
      setInvoiceLoading(false);
    }
  };

  // Handle unsaved changes warning actions
  const handleUnsavedWarningAction = async (action) => {
    if (action === 'save') {
      await saveInvoice();
    }
    
    setShowUnsavedWarning(false);
    
    if (pendingNavigation) {
      if (pendingNavigation.type === 'selectInvoice') {
        await loadInvoice(pendingNavigation.invoiceId);
      } else if (pendingNavigation.type === 'newInvoice') {
        startNewInvoice();
      }
      setPendingNavigation(null);
    }
  };

  // Create new invoice
  const startNewInvoice = () => {
    setSelectedInvoiceId(null);
    setInvoiceData(null);
    setIsCreating(true);
    const newFormData = {
      client_id: '',
      trip_id: '',
      display_currency: 'ZAR',
      issue_date: new Date().toISOString().split('T')[0],
      due_date: '',
      payment_terms: '',
      payment_terms_custom: ''
    };
    setFormData(newFormData);
    setLineItems([]);
    setAdjustments([]);
    setClientDefaultRate(0);
    
    // Reset dirty state
    setInitialFormData(newFormData);
    setInitialLineItems([]);
    setInitialAdjustments([]);
  };

  // Handle client selection with auto-population
  const handleClientChange = async (clientId) => {
    setFormData(prev => ({ ...prev, client_id: clientId }));
    
    if (clientId) {
      try {
        // Fetch client details
        const clientResponse = await axios.get(`${API}/clients/${clientId}`, { withCredentials: true });
        const client = clientResponse.data;
        
        // Auto-populate default currency if client has one
        if (client.default_currency) {
          setFormData(prev => ({ ...prev, display_currency: client.default_currency }));
        }
        
        // Fetch client rate
        const rate = await fetchClientRate(clientId);
        
        // Update existing line items with new rate if they have default rate
        if (rate && lineItems.length > 0) {
          setLineItems(prevItems => prevItems.map(item => {
            // Only update items that are using the default rate
            if (item.rate === clientDefaultRate || item.rate === 36) {
              const newAmount = (parseFloat(item.quantity) || 0) * rate;
              return { ...item, rate, amount: newAmount };
            }
            return item;
          }));
        }
      } catch (error) {
        console.error('Failed to fetch client details:', error);
      }
    }
  };

  // Add line item
  const addLineItem = () => {
    setLineItems([...lineItems, {
      id: `item-${Date.now()}`,
      description: '',
      quantity: 1,
      unit: 'kg',
      rate: clientDefaultRate || 36,
      amount: clientDefaultRate || 36
    }]);
  };

  const updateLineItem = (id, field, value) => {
    setLineItems(lineItems.map(item => {
      if (item.id !== id) return item;
      const updated = { ...item, [field]: value };
      if (field === 'quantity' || field === 'rate') {
        updated.amount = (parseFloat(updated.quantity) || 0) * (parseFloat(updated.rate) || 0);
      }
      return updated;
    }));
  };

  // Remove line item and clear invoice linkage in backend
  const removeLineItem = async (id) => {
    // Find the line item to get shipment_id
    const lineItem = lineItems.find(item => item.id === id);
    
    if (lineItem?.shipment_id) {
      try {
        // Clear invoice_id on the parcel in backend
        await axios.patch(`${API}/shipments/${lineItem.shipment_id}`, {
          invoice_id: null
        }, { withCredentials: true });
      } catch (error) {
        console.error('Failed to clear parcel invoice linkage:', error);
        // Continue with removal even if backend update fails
      }
    }
    
    // Remove from frontend
    setLineItems(lineItems.filter(item => item.id !== id));
  };

  // Adjustments
  const addAdjustment = (isAddition = false) => {
    setAdjustments([...adjustments, {
      id: `adj-${Date.now()}`,
      description: isAddition ? 'Additional charge' : 'Discount',
      amount: 0,
      is_addition: isAddition
    }]);
  };

  const updateAdjustment = (id, field, value) => {
    setAdjustments(adjustments.map(adj => 
      adj.id === id ? { ...adj, [field]: value } : adj
    ));
  };

  const removeAdjustment = (id) => {
    setAdjustments(adjustments.filter(adj => adj.id !== id));
  };

  // Save invoice with validation
  const saveInvoice = async (finalize = false) => {
    if (!formData.client_id) {
      toast.error('Please select a client');
      return false;
    }
    if (lineItems.length === 0) {
      toast.error('Please add at least one line item');
      return false;
    }

    // Validate invoice total matches calculated total
    const calculatedSubtotal = lineItems.reduce((sum, item) => sum + (parseFloat(item.amount) || 0), 0);
    const calculatedAdjustments = adjustments.reduce((sum, adj) => {
      const amount = parseFloat(adj.amount) || 0;
      return sum + (adj.is_addition ? amount : -amount);
    }, 0);
    const calculatedTotal = calculatedSubtotal + calculatedAdjustments;
    
    // Check for mismatch (with small tolerance for floating point)
    if (Math.abs(calculatedTotal - totals.total) > 0.01) {
      toast.error(`Invoice total mismatch. Calculated: ${formatCurrency(calculatedTotal)}, Expected: ${formatCurrency(totals.total)}`);
      return false;
    }

    setSubmitting(true);
    try {
      const payload = {
        client_id: formData.client_id,
        trip_id: formData.trip_id || null,
        currency: formData.display_currency,
        issue_date: formData.issue_date,
        due_date: formData.due_date || null,
        payment_terms: formData.payment_terms || null,
        payment_terms_custom: formData.payment_terms_custom || null,
        line_items: lineItems,
        adjustments: adjustments,
        total: totals.total,
        status: finalize ? 'sent' : 'draft'
      };

      if (selectedInvoiceId) {
        await axios.put(`${API}/invoices/${selectedInvoiceId}`, payload, { withCredentials: true });
        toast.success(finalize ? 'Invoice finalized!' : 'Invoice updated');
      } else {
        const response = await axios.post(`${API}/invoices`, payload, { withCredentials: true });
        setSelectedInvoiceId(response.data.id);
        toast.success('Invoice created');
      }
      
      // Reset dirty state after successful save
      setInitialFormData({ ...formData });
      setInitialLineItems([...lineItems]);
      setInitialAdjustments([...adjustments]);
      
      fetchInvoices();
      if (selectedInvoiceId) loadInvoice(selectedInvoiceId);
      return true;
    } catch (error) {
      toast.error('Failed to save invoice');
      return false;
    } finally {
      setSubmitting(false);
    }
  };

  // Download PDF
  const downloadPdf = async (invoiceId) => {
    try {
      const response = await axios.get(`${API}/invoices/${invoiceId}/pdf`, {
        withCredentials: true,
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `invoice_${invoiceId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast.success('PDF downloaded');
    } catch (error) {
      toast.error('Failed to download PDF');
    }
  };

  // Delete draft invoice
  const deleteInvoice = async () => {
    if (!selectedInvoiceId) return;
    
    if (!window.confirm('Are you sure you want to delete this draft invoice? This action cannot be undone.')) {
      return;
    }
    
    setSubmitting(true);
    try {
      await axios.delete(`${API}/invoices/${selectedInvoiceId}`, { withCredentials: true });
      toast.success('Invoice deleted');
      setSelectedInvoiceId(null);
      setInvoiceData(null);
      setLineItems([]);
      setAdjustments([]);
      fetchInvoices();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete invoice');
    } finally {
      setSubmitting(false);
    }
  };

  // Record payment
  const recordPayment = async () => {
    if (!paymentForm.amount || parseFloat(paymentForm.amount) <= 0) {
      toast.error('Please enter a valid amount');
      return;
    }

    setSubmitting(true);
    try {
      await axios.post(`${API}/invoices/${selectedInvoiceId}/record-payment`, {
        amount: parseFloat(paymentForm.amount),
        payment_date: paymentForm.payment_date,
        payment_method: paymentForm.payment_method,
        reference: paymentForm.reference,
        notes: paymentForm.notes
      }, { withCredentials: true });
      
      toast.success('Payment recorded');
      setPaymentDialogOpen(false);
      setPaymentForm({
        amount: '',
        payment_date: new Date().toISOString().split('T')[0],
        payment_method: 'bank_transfer',
        reference: '',
        notes: ''
      });
      fetchInvoices();
      selectInvoice(selectedInvoiceId);
    } catch (error) {
      toast.error('Failed to record payment');
    } finally {
      setSubmitting(false);
    }
  };

  // Add parcels from trip - using smart selection endpoint
  const fetchTripParcels = async (tripId) => {
    try {
      // Reset selection state when opening modal
      setSelectedParcels(new Set());
      setReassignWarning(null);
      
      const response = await axios.get(`${API}/invoices/trip-parcels/${tripId}`, { withCredentials: true });
      setAvailableParcels(response.data || []);
      setParcelsDialogOpen(true);
    } catch (error) {
      toast.error('Failed to fetch parcels');
    }
  };

  // Reassign parcels from another invoice
  const reassignParcels = async (parcelIds) => {
    try {
      await axios.post(`${API}/invoices/${selectedInvoiceId}/reassign-parcels`, parcelIds, { 
        withCredentials: true 
      });
      toast.success('Parcels reassigned');
      setReassignWarning(null);
      fetchTripParcels(formData.trip_id);
      selectInvoice(selectedInvoiceId);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to reassign parcels');
    }
  };

  const addSelectedParcels = () => {
    const rate = clientDefaultRate || 36;
    
    // Check for invoiced parcels
    const invoicedParcels = Array.from(selectedParcels)
      .map(id => availableParcels.find(p => p.id === id))
      .filter(p => p && p.is_invoiced);
    
    if (invoicedParcels.length > 0) {
      setReassignWarning({
        parcels: invoicedParcels,
        message: `${invoicedParcels.length} parcel(s) are already invoiced. Reassign them to this invoice?`
      });
      return;
    }
    
    // Get client info
    const client = clients.find(c => c.id === formData.client_id);
    
    const newItems = Array.from(selectedParcels).map(parcelId => {
      const parcel = availableParcels.find(p => p.id === parcelId);
      if (!parcel) return null;
      
      const weight = parcel.total_weight || 1;
      return {
        id: `item-${Date.now()}-${parcelId}`,
        shipment_id: parcel.id,
        description: parcel.description || 'Shipment',
        quantity: parseInt(parcel.quantity) || 1,
        weight: weight,
        unit: 'kg',
        rate: rate,
        amount: weight * rate,
        parcel_label: parcel.parcel_label || '',
        client_name: client?.name || parcel.client_name,
        recipient_name: parcel.recipient || '',
        length_cm: parcel.length_cm,
        width_cm: parcel.width_cm,
        height_cm: parcel.height_cm
      };
    }).filter(Boolean);
    
    setLineItems([...lineItems, ...newItems]);
    setParcelsDialogOpen(false);
    setSelectedParcels(new Set());
  };

  // Fetch parcels from warehouse for adding to invoice
  const fetchWarehouseParcels = async () => {
    setLoadingWarehouseParcels(true);
    try {
      const response = await axios.get(`${API}/shipments`, { 
        withCredentials: true,
        params: {
          status: 'warehouse,staged,loaded',
          not_invoiced: 'true',  // Only parcels without invoice
          limit: 500
        }
      });
      
      // Also filter out parcels that are already in the current invoice's line items
      const existingShipmentIds = new Set(lineItems.map(li => li.shipment_id).filter(Boolean));
      const availableForInvoice = (response.data || []).filter(p => 
        !existingShipmentIds.has(p.id) && !p.invoice_id
      );
      
      setWarehouseParcels(availableForInvoice);
      setWarehouseDialogOpen(true);
      setSelectedWarehouseParcels(new Set());
    } catch (error) {
      toast.error('Failed to fetch warehouse parcels');
    } finally {
      setLoadingWarehouseParcels(false);
    }
  };

  // Add selected warehouse parcels to line items
  const addSelectedWarehouseParcels = () => {
    const rate = clientDefaultRate || 36;
    const client = clients.find(c => c.id === formData.client_id);
    
    const newItems = Array.from(selectedWarehouseParcels).map(parcelId => {
      const parcel = warehouseParcels.find(p => p.id === parcelId);
      if (!parcel) return null;
      
      const weight = parcel.total_weight || 1;
      const volWeight = parcel.length_cm && parcel.width_cm && parcel.height_cm
        ? (parcel.length_cm * parcel.width_cm * parcel.height_cm) / 5000
        : 0;
      const shipWeight = Math.max(weight, volWeight);
      
      return {
        id: `item-${Date.now()}-${parcelId}`,
        shipment_id: parcel.id,
        description: parcel.description || 'Shipment',
        quantity: parseInt(parcel.quantity) || 1,
        weight: weight,
        unit: 'kg',
        rate: rate,
        amount: shipWeight * rate,
        parcel_label: parcel.parcel_label || '',
        client_name: client?.name || parcel.client_name,
        recipient_name: parcel.recipient || '',
        length_cm: parcel.length_cm,
        width_cm: parcel.width_cm,
        height_cm: parcel.height_cm
      };
    }).filter(Boolean);
    
    setLineItems([...lineItems, ...newItems]);
    setWarehouseDialogOpen(false);
    setSelectedWarehouseParcels(new Set());
    setWarehouseSearch('');
    toast.success(`Added ${newItems.length} parcel(s) to invoice`);
  };

  // Filter warehouse parcels
  const filteredWarehouseParcels = useMemo(() => {
    return warehouseParcels.filter(p => {
      // Warehouse filter
      if (warehouseFilter !== 'all' && p.warehouse_id !== warehouseFilter) return false;
      // Client filter  
      if (warehouseClientFilter !== 'all' && p.client_id !== warehouseClientFilter) return false;
      // Search filter
      if (warehouseSearch) {
        const search = warehouseSearch.toLowerCase();
        const matchesDesc = (p.description || '').toLowerCase().includes(search);
        const matchesBarcode = (p.barcode || '').toLowerCase().includes(search);
        const matchesRecipient = (p.recipient || '').toLowerCase().includes(search);
        if (!matchesDesc && !matchesBarcode && !matchesRecipient) return false;
      }
      return true;
    });
  }, [warehouseParcels, warehouseFilter, warehouseClientFilter, warehouseSearch]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-6 gap-6" data-testid="invoice-editor">
      {/* Left Panel - Invoice List (1/6) */}
      <div className="lg:col-span-1 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-[#3C3F42]">Invoices</h3>
          <Button 
            onClick={startNewInvoice}
            className="bg-[#6B633C] hover:bg-[#5a5332]"
            data-testid="new-invoice-btn"
          >
            <Plus className="h-4 w-4 mr-2" /> New Invoice
          </Button>
        </div>

        {/* Filters */}
        <div className="flex gap-2">
          <Select value={tripFilter} onValueChange={setTripFilter}>
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="All Trips" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Trips</SelectItem>
              {trips.map(trip => (
                <SelectItem key={trip.id} value={trip.id}>{trip.trip_number}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="All Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="draft">Draft</SelectItem>
              <SelectItem value="sent">Sent</SelectItem>
              <SelectItem value="paid">Paid</SelectItem>
              <SelectItem value="overdue">Overdue</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Invoice List */}
        <Card className="border border-gray-200">
          <ScrollArea className="h-[500px]">
            {loading ? (
              <div className="p-4 text-center">
                <Loader2 className="h-6 w-6 animate-spin mx-auto text-gray-400" />
              </div>
            ) : invoices.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                No invoices found
              </div>
            ) : (
              <div className="divide-y">
                {invoices.map(inv => (
                  <div
                    key={inv.id}
                    onClick={() => selectInvoice(inv.id)}
                    className={cn(
                      "p-4 cursor-pointer hover:bg-gray-50 transition-colors",
                      selectedInvoiceId === inv.id && "bg-[#E8E4D0]/30 border-l-4 border-[#6B633C]"
                    )}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-mono font-medium text-sm">{inv.invoice_number}</span>
                      <Badge className={cn(
                        "text-xs",
                        statusConfig[inv.status]?.bg,
                        statusConfig[inv.status]?.text
                      )}>
                        {statusConfig[inv.status]?.label || inv.status}
                      </Badge>
                    </div>
                    <p className="text-sm text-gray-600">{inv.client_name}</p>
                    <div className="flex justify-between mt-2 text-sm">
                      <span className="text-gray-500">{inv.trip_number || 'No trip'}</span>
                      <span className="font-medium">R {(inv.total || 0).toLocaleString('en-ZA', { minimumFractionDigits: 2 })}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </ScrollArea>
        </Card>
      </div>

      {/* Right Panel - Invoice Editor (5/6 = ~80%) */}
      <div className="lg:col-span-5">
        {!selectedInvoiceId && !isCreating ? (
          <Card className="border border-gray-200 h-full flex items-center justify-center">
            <div className="text-center p-8">
              <Receipt className="h-16 w-16 mx-auto text-gray-300 mb-4" />
              <h3 className="text-lg font-medium text-gray-500">Select an invoice or create new</h3>
              <Button 
                onClick={startNewInvoice}
                className="mt-4 bg-[#6B633C] hover:bg-[#5a5332]"
              >
                <Plus className="h-4 w-4 mr-2" /> New Invoice
              </Button>
            </div>
          </Card>
        ) : invoiceLoading ? (
          <Card className="border border-gray-200 h-full flex items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
          </Card>
        ) : (
          <Card className="border border-gray-200">
            <CardHeader className="border-b bg-gray-50 pb-4">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">
                  {isCreating ? 'New Invoice' : `Invoice ${invoiceData?.invoice_number || ''}`}
                </CardTitle>
                <div className="flex items-center gap-2">
                  {/* Currency Toggle */}
                  <div className="flex items-center gap-2 bg-white border rounded-lg px-3 py-1.5">
                    <span className={cn("text-sm font-medium", formData.display_currency === 'ZAR' ? "text-[#6B633C]" : "text-gray-400")}>ZAR</span>
                    <Switch
                      checked={formData.display_currency === 'KES'}
                      onCheckedChange={(checked) => setFormData(prev => ({ ...prev, display_currency: checked ? 'KES' : 'ZAR' }))}
                    />
                    <span className={cn("text-sm font-medium", formData.display_currency === 'KES' ? "text-[#6B633C]" : "text-gray-400")}>KES</span>
                  </div>
                  {invoiceData && (
                    <Badge className={cn(statusConfig[invoiceData.status]?.bg, statusConfig[invoiceData.status]?.text)}>
                      {statusConfig[invoiceData.status]?.label}
                    </Badge>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-6 space-y-6">
              {/* Client & Trip Selection */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Client *</Label>
                  <Select 
                    value={formData.client_id} 
                    onValueChange={handleClientChange}
                    disabled={invoiceData?.status === 'paid'}
                  >
                    <SelectTrigger data-testid="client-select">
                      <SelectValue placeholder="Select client" />
                    </SelectTrigger>
                    <SelectContent>
                      {clients.map(client => (
                        <SelectItem key={client.id} value={client.id}>{client.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {/* Client info display */}
                  {formData.client_id && (
                    <div className="mt-1 text-xs text-muted-foreground">
                      {clients.find(c => c.id === formData.client_id)?.vat_number && (
                        <span>VAT: {clients.find(c => c.id === formData.client_id)?.vat_number}</span>
                      )}
                      {clientDefaultRate > 0 && (
                        <span className="ml-2">Rate: R {clientDefaultRate.toFixed(2)}/kg</span>
                      )}
                    </div>
                  )}
                </div>
                <div>
                  <Label>Trip (optional)</Label>
                  <Select 
                    value={formData.trip_id} 
                    onValueChange={(value) => setFormData(prev => ({ ...prev, trip_id: value === 'none' ? '' : value }))}
                    disabled={invoiceData?.status === 'paid'}
                  >
                    <SelectTrigger data-testid="trip-select">
                      <SelectValue placeholder="Select trip" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">No trip</SelectItem>
                      {trips.map(trip => (
                        <SelectItem key={trip.id} value={trip.id}>{trip.trip_number}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Dates */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Issue Date</Label>
                  <Input
                    type="date"
                    value={formData.issue_date}
                    onChange={(e) => setFormData(prev => ({ ...prev, issue_date: e.target.value }))}
                    disabled={invoiceData?.status === 'paid'}
                  />
                </div>
                <div>
                  <Label>Due Date</Label>
                  <Input
                    type="date"
                    value={formData.due_date}
                    onChange={(e) => setFormData(prev => ({ ...prev, due_date: e.target.value }))}
                    disabled={invoiceData?.status === 'paid'}
                  />
                </div>
              </div>

              {/* Payment Terms */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Payment Terms</Label>
                  <Select 
                    value={formData.payment_terms || ''} 
                    onValueChange={(value) => setFormData(prev => ({ ...prev, payment_terms: value }))}
                    disabled={invoiceData?.status === 'paid'}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select payment terms" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">No terms specified</SelectItem>
                      {paymentTermsOptions.map(opt => (
                        <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                {formData.payment_terms === 'custom' && (
                  <div>
                    <Label>Custom Terms</Label>
                    <Input
                      value={formData.payment_terms_custom || ''}
                      onChange={(e) => setFormData(prev => ({ ...prev, payment_terms_custom: e.target.value }))}
                      placeholder="Enter custom terms..."
                      disabled={invoiceData?.status === 'paid'}
                    />
                  </div>
                )}
              </div>

              {/* Line Items with Enhanced Columns */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-4">
                    <Label>Line Items</Label>
                    <span className="text-sm text-gray-500">
                      {lineItems.length} items | Total Qty: {totals.totalQty} pieces
                    </span>
                  </div>
                  <div className="flex gap-2">
                    {selectedLineItems.size > 0 && (
                      <Button 
                        variant="outline" 
                        size="sm" 
                        onClick={() => setBatchRateDialogOpen(true)}
                        className="text-[#6B633C]"
                      >
                        Adjust Rate ({selectedLineItems.size})
                      </Button>
                    )}
                    {formData.trip_id && (
                      <Button variant="outline" size="sm" onClick={() => fetchTripParcels(formData.trip_id)}>
                        <FileText className="h-3 w-3 mr-1" /> Add from Trip
                      </Button>
                    )}
                    <Button variant="outline" size="sm" onClick={fetchWarehouseParcels} disabled={loadingWarehouseParcels}>
                      {loadingWarehouseParcels ? (
                        <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                      ) : (
                        <Building2 className="h-3 w-3 mr-1" />
                      )}
                      Add from Warehouse
                    </Button>
                  </div>
                </div>
                
                {/* Reverse Calculator */}
                <div className="flex items-center gap-2 mb-3 p-2 bg-gray-50 rounded-lg">
                  <Label className="text-sm whitespace-nowrap">Target Total:</Label>
                  <Input
                    type="number"
                    value={targetTotal}
                    onChange={(e) => setTargetTotal(e.target.value)}
                    placeholder="Enter target amount"
                    className="w-[150px] h-8"
                  />
                  <Button size="sm" variant="outline" onClick={handleCalculateRate}>
                    Calculate Rate
                  </Button>
                  {calculatedRate && (
                    <>
                      <span className="text-sm text-[#6B633C] font-medium">
                        = R {calculatedRate}/kg
                      </span>
                      <Button size="sm" onClick={applyCalculatedRate} className="bg-[#6B633C] hover:bg-[#5a5332]">
                        Apply
                      </Button>
                    </>
                  )}
                </div>

                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-gray-50">
                        <TableHead className="w-[40px]">
                          <Checkbox 
                            checked={selectedLineItems.size === lineItems.length && lineItems.length > 0}
                            onCheckedChange={toggleAllLineItems}
                          />
                        </TableHead>
                        <TableHead className="w-[50px] text-center">#</TableHead>
                        <TableHead className="w-[100px]">Recipient</TableHead>
                        <TableHead className="min-w-[140px] max-w-[200px]">Description</TableHead>
                        <TableHead className="w-[70px] text-right">Qty</TableHead>
                        <TableHead className="w-[85px] text-right">KG</TableHead>
                        <TableHead className="w-[50px] text-right">L</TableHead>
                        <TableHead className="w-[50px] text-right">W</TableHead>
                        <TableHead className="w-[50px] text-right">H</TableHead>
                        <TableHead className="w-[85px] text-right">Vol Wt</TableHead>
                        <TableHead className="w-[90px] text-right">Ship Wt</TableHead>
                        <TableHead style={{ maxWidth: '80px' }} className="w-[70px] text-right">Rate</TableHead>
                        <TableHead style={{ minWidth: '140px' }} className="text-right">Amount</TableHead>
                        <TableHead className="w-[40px]"></TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {lineItems.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={14} className="text-center py-8 text-gray-400">
                            No line items. Click "Add from Trip" or "Add from Warehouse" to add parcels.
                          </TableCell>
                        </TableRow>
                      ) : (
                        lineItems.map((item, idx) => {
                          const { qty, weight } = getItemDisplayValues(item);
                          const volWeight = calculateVolumetricWeight(item.length_cm, item.width_cm, item.height_cm);
                          const actualWeight = parseFloat(weight) || 0;
                          const shipWeight = getShippingWeight(actualWeight, volWeight);
                          const isVolumetric = volWeight && volWeight > actualWeight;
                          
                          return (
                            <TableRow key={item.id} className={cn(selectedLineItems.has(item.id) && "bg-[#6B633C]/5")}>
                              <TableCell>
                                <Checkbox 
                                  checked={selectedLineItems.has(item.id)}
                                  onCheckedChange={() => toggleLineItemSelection(item.id)}
                                />
                              </TableCell>
                              <TableCell className="text-center text-xs text-gray-500 font-mono">
                                {idx + 1}
                              </TableCell>
                              <TableCell className="text-xs truncate max-w-[100px]" title={item.recipient_name}>
                                {item.recipient_name || '-'}
                              </TableCell>
                              <TableCell className="max-w-[200px] text-xs" title={item.description}>
                                <span className="truncate block">{item.description || '-'}</span>
                              </TableCell>
                              <TableCell className="text-right font-mono text-xs">
                                {qty}
                              </TableCell>
                              <TableCell className="text-right font-mono text-xs">
                                {actualWeight ? actualWeight.toFixed(2) : '-'}
                              </TableCell>
                              <TableCell className="text-right font-mono text-xs">
                                {item.length_cm ? parseFloat(item.length_cm).toFixed(0) : '-'}
                              </TableCell>
                              <TableCell className="text-right font-mono text-xs">
                                {item.width_cm ? parseFloat(item.width_cm).toFixed(0) : '-'}
                              </TableCell>
                              <TableCell className="text-right font-mono text-xs">
                                {item.height_cm ? parseFloat(item.height_cm).toFixed(0) : '-'}
                              </TableCell>
                              <TableCell className="text-right font-mono text-xs">
                                {volWeight ? volWeight.toFixed(2) : '-'}
                              </TableCell>
                              <TableCell className={cn(
                                "text-right font-mono text-xs font-semibold",
                                isVolumetric ? "text-amber-600" : "text-green-700"
                              )}>
                                {shipWeight.toFixed(2)}
                              </TableCell>
                              <TableCell style={{ maxWidth: '80px' }}>
                                <Input
                                  type="number"
                                  value={item.rate}
                                  onChange={(e) => updateLineItem(item.id, 'rate', e.target.value)}
                                  disabled={invoiceData?.status === 'paid'}
                                  className="w-[60px] text-sm h-8 text-right"
                                />
                              </TableCell>
                              <TableCell className="text-right font-mono text-sm font-medium" style={{ minWidth: '140px' }}>
                                {formatCurrency(item.amount)}
                              </TableCell>
                              <TableCell>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  onClick={() => removeLineItem(item.id)}
                                  disabled={invoiceData?.status === 'paid'}
                                  className="h-8 w-8"
                                >
                                  <Trash2 className="h-3 w-3 text-red-500" />
                                </Button>
                              </TableCell>
                            </TableRow>
                          );
                        })
                      )}
                    </TableBody>
                  </Table>
                </div>
              </div>

              {/* Adjustments */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <Label>Adjustments</Label>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={() => addAdjustment(false)} disabled={invoiceData?.status === 'paid'}>
                      Discount
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => addAdjustment(true)} disabled={invoiceData?.status === 'paid'}>
                      + Charge
                    </Button>
                  </div>
                </div>
                {adjustments.map(adj => (
                  <div key={adj.id} className="flex items-center gap-2 mb-2">
                    <Input
                      value={adj.description}
                      onChange={(e) => updateAdjustment(adj.id, 'description', e.target.value)}
                      className="flex-1"
                      disabled={invoiceData?.status === 'paid'}
                    />
                    <div className="flex items-center">
                      <span className={cn("mr-1 font-bold", adj.is_addition ? "text-green-600" : "text-red-600")}>
                        {adj.is_addition ? '+' : '-'}
                      </span>
                      <Input
                        type="number"
                        value={adj.amount}
                        onChange={(e) => updateAdjustment(adj.id, 'amount', e.target.value)}
                        className="w-[140px] text-right"
                        disabled={invoiceData?.status === 'paid'}
                      />
                    </div>
                    <Button variant="ghost" size="icon" onClick={() => removeAdjustment(adj.id)} disabled={invoiceData?.status === 'paid'}>
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>

              {/* Totals - Live Calculation Breakdown */}
              <div className="border-t pt-4 space-y-2">
                <div className="text-xs text-muted-foreground uppercase font-medium mb-2">Calculation Breakdown</div>
                <div className="flex justify-between text-sm">
                  <span>Line items subtotal ({lineItems.length} items)</span>
                  <span className="font-mono">{formatCurrency(totals.subtotal)}</span>
                </div>
                {adjustments.map((adj, idx) => (
                  <div key={adj.id || idx} className="flex justify-between text-sm pl-4">
                    <span className="text-gray-600">{adj.is_addition ? '+' : '-'} {adj.description || 'Adjustment'}</span>
                    <span className={cn("font-mono", adj.is_addition ? "text-green-600" : "text-red-600")}>
                      {adj.is_addition ? '+' : '-'}{formatCurrency(parseFloat(adj.amount) || 0)}
                    </span>
                  </div>
                ))}
                {totals.adjustmentTotal !== 0 && (
                  <div className="flex justify-between text-sm border-t pt-1">
                    <span className="font-medium">Adjustments Total</span>
                    <span className={cn("font-mono font-medium", totals.adjustmentTotal > 0 ? "text-green-600" : "text-red-600")}>
                      {totals.adjustmentTotal > 0 ? '+' : ''}{formatCurrency(totals.adjustmentTotal)}
                    </span>
                  </div>
                )}
                <div className="flex justify-between text-lg font-bold border-t pt-2 mt-2">
                  <span>Total</span>
                  <span className="font-mono text-[#6B633C]">{formatCurrency(totals.total)}</span>
                </div>
                {invoiceData?.paid_amount > 0 && (
                  <>
                    <div className="flex justify-between text-sm text-green-600">
                      <span>Paid</span>
                      <span className="font-mono">-{formatCurrency(invoiceData.paid_amount)}</span>
                    </div>
                    <div className="flex justify-between text-lg font-bold text-red-600">
                      <span>Outstanding</span>
                      <span className="font-mono">{formatCurrency(totals.total - invoiceData.paid_amount)}</span>
                    </div>
                  </>
                )}
                
                {/* Unsaved Changes Indicator */}
                {hasUnsavedChanges && (
                  <div className="flex items-center gap-2 p-2 bg-amber-50 border border-amber-200 rounded text-sm text-amber-700 mt-2">
                    <AlertTriangle className="h-4 w-4" />
                    <span>You have unsaved changes</span>
                  </div>
                )}
              </div>

              {/* Actions */}
              <div className="flex gap-2 pt-4 border-t">
                <Button
                  onClick={() => saveInvoice(false)}
                  disabled={submitting}
                  variant="outline"
                >
                  {submitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                  Save Draft
                </Button>
                {invoiceData?.status !== 'paid' && (
                  <Button
                    onClick={() => saveInvoice(true)}
                    disabled={submitting}
                    className="bg-[#6B633C] hover:bg-[#5a5332]"
                  >
                    {submitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Send className="h-4 w-4 mr-2" />}
                    Finalize Invoice
                  </Button>
                )}
                {selectedInvoiceId && (
                  <>
                    <Button
                      variant="outline"
                      onClick={() => downloadPdf(selectedInvoiceId)}
                      data-testid="download-pdf-btn"
                    >
                      <Download className="h-4 w-4 mr-2" /> Download PDF
                    </Button>
                    {invoiceData?.status !== 'paid' && invoiceData?.status !== 'draft' && (
                      <Button
                        variant="outline"
                        onClick={() => setPaymentDialogOpen(true)}
                      >
                        <DollarSign className="h-4 w-4 mr-2" /> Record Payment
                      </Button>
                    )}
                    {invoiceData?.status === 'draft' && (
                      <Button
                        variant="destructive"
                        onClick={deleteInvoice}
                        disabled={submitting}
                        data-testid="delete-invoice-btn"
                      >
                        <Trash2 className="h-4 w-4 mr-2" /> Delete Invoice
                      </Button>
                    )}
                  </>
                )}
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Payment Dialog */}
      <Dialog open={paymentDialogOpen} onOpenChange={setPaymentDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Record Payment</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label>Amount</Label>
              <Input
                type="number"
                value={paymentForm.amount}
                onChange={(e) => setPaymentForm(prev => ({ ...prev, amount: e.target.value }))}
                placeholder="0.00"
              />
            </div>
            <div>
              <Label>Payment Date</Label>
              <Input
                type="date"
                value={paymentForm.payment_date}
                onChange={(e) => setPaymentForm(prev => ({ ...prev, payment_date: e.target.value }))}
              />
            </div>
            <div>
              <Label>Payment Method</Label>
              <Select value={paymentForm.payment_method} onValueChange={(value) => setPaymentForm(prev => ({ ...prev, payment_method: value }))}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(paymentMethodConfig).map(([key, config]) => (
                    <SelectItem key={key} value={key}>{config.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Reference</Label>
              <Input
                value={paymentForm.reference}
                onChange={(e) => setPaymentForm(prev => ({ ...prev, reference: e.target.value }))}
                placeholder="Transaction reference"
              />
            </div>
            <div>
              <Label>Notes</Label>
              <Textarea
                value={paymentForm.notes}
                onChange={(e) => setPaymentForm(prev => ({ ...prev, notes: e.target.value }))}
                placeholder="Optional notes"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPaymentDialogOpen(false)}>Cancel</Button>
            <Button onClick={recordPayment} disabled={submitting} className="bg-[#6B633C] hover:bg-[#5a5332]">
              {submitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              Record Payment
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add Parcels Dialog */}
      <Dialog open={parcelsDialogOpen} onOpenChange={setParcelsDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Add Parcels from Trip</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            {/* Reassign Warning */}
            {reassignWarning && (
              <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="h-5 w-5 text-yellow-600 mt-0.5" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-yellow-800">{reassignWarning.message}</p>
                    <div className="mt-2 space-y-1">
                      {reassignWarning.parcels.map(p => (
                        <p key={p.id} className="text-xs text-yellow-700">
                          • {p.description} - currently in {p.invoice_number}
                        </p>
                      ))}
                    </div>
                    <div className="mt-3 flex gap-2">
                      <Button 
                        size="sm"
                        variant="outline"
                        onClick={() => setReassignWarning(null)}
                      >
                        Cancel
                      </Button>
                      <Button 
                        size="sm"
                        className="bg-yellow-600 hover:bg-yellow-700"
                        onClick={() => reassignParcels(reassignWarning.parcels.map(p => p.id))}
                      >
                        Reassign to This Invoice
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            )}
            
            <ScrollArea className="h-[350px]">
              {availableParcels.length === 0 ? (
                <p className="text-center text-gray-500 py-8">No parcels found for this trip</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow className="bg-gray-50">
                      <TableHead className="w-[40px]"></TableHead>
                      <TableHead>Parcel #</TableHead>
                      <TableHead>Client</TableHead>
                      <TableHead>Recipient</TableHead>
                      <TableHead>Description</TableHead>
                      <TableHead className="text-right">Weight</TableHead>
                      <TableHead>Current Invoice</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {availableParcels.map(parcel => (
                      <TableRow 
                        key={parcel.id} 
                        className={cn(
                          parcel.is_invoiced && "bg-gray-50 opacity-60"
                        )}
                      >
                        <TableCell>
                          <Checkbox
                            checked={selectedParcels.has(parcel.id)}
                            onCheckedChange={(checked) => {
                              const newSet = new Set(selectedParcels);
                              if (checked) newSet.add(parcel.id);
                              else newSet.delete(parcel.id);
                              setSelectedParcels(newSet);
                            }}
                          />
                        </TableCell>
                        <TableCell className="font-mono text-sm">
                          {parcel.parcel_label || parcel.id.slice(0, 8)}
                        </TableCell>
                        <TableCell className="text-sm">{parcel.client_name}</TableCell>
                        <TableCell className="text-sm max-w-[100px] truncate" title={parcel.recipient}>
                          {parcel.recipient || '-'}
                        </TableCell>
                        <TableCell className="text-sm max-w-[130px] truncate" title={parcel.description}>
                          {parcel.description}
                        </TableCell>
                        <TableCell className="text-right text-sm">{parcel.total_weight?.toFixed(2)} kg</TableCell>
                        <TableCell>
                          {parcel.is_invoiced ? (
                            <Badge variant="outline" className="text-xs bg-yellow-50 text-yellow-700 border-yellow-200">
                              {parcel.invoice_number}
                            </Badge>
                          ) : (
                            <span className="text-xs text-gray-400">-</span>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </ScrollArea>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setParcelsDialogOpen(false)}>Cancel</Button>
            <Button 
              onClick={addSelectedParcels} 
              disabled={selectedParcels.size === 0}
              className="bg-[#6B633C] hover:bg-[#5a5332]"
            >
              Add {selectedParcels.size} Parcel(s)
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Batch Rate Dialog */}
      <Dialog open={batchRateDialogOpen} onOpenChange={setBatchRateDialogOpen}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>Adjust Rate for Selected Items</DialogTitle>
          </DialogHeader>
          <div className="py-4 space-y-4">
            <p className="text-sm text-gray-600">
              Apply new rate to {selectedLineItems.size} selected item(s)
            </p>
            <div className="space-y-2">
              <Label>New Rate (per kg)</Label>
              <Input
                type="number"
                value={batchRate}
                onChange={(e) => setBatchRate(e.target.value)}
                placeholder="Enter rate..."
                step="0.01"
              />
            </div>
            {calculatedRate && (
              <p className="text-sm text-[#6B633C]">
                Suggested rate from calculator: R {calculatedRate}
              </p>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setBatchRateDialogOpen(false)}>Cancel</Button>
            <Button 
              onClick={handleBatchRateUpdate}
              disabled={!batchRate}
              className="bg-[#6B633C] hover:bg-[#5a5332]"
            >
              Apply Rate
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Unsaved Changes Warning Dialog */}
      <AlertDialog open={showUnsavedWarning} onOpenChange={setShowUnsavedWarning}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Unsaved Changes</AlertDialogTitle>
            <AlertDialogDescription>
              You have unsaved changes to {invoiceData?.invoice_number || 'this invoice'}. 
              Would you like to save before leaving?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => {
              setShowUnsavedWarning(false);
              setPendingNavigation(null);
            }}>
              Stay on Page
            </AlertDialogCancel>
            <Button
              variant="outline"
              onClick={() => handleUnsavedWarningAction('discard')}
            >
              Leave Without Saving
            </Button>
            <Button
              onClick={() => handleUnsavedWarningAction('save')}
              className="bg-[#6B633C] hover:bg-[#5a5332]"
            >
              <Save className="h-4 w-4 mr-2" />
              Save and Leave
            </Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Add Parcels from Warehouse Dialog */}
      <Dialog open={warehouseDialogOpen} onOpenChange={setWarehouseDialogOpen}>
        <DialogContent className="max-w-4xl">
          <DialogHeader>
            <DialogTitle>Add Parcels from Warehouse</DialogTitle>
          </DialogHeader>
          <div className="py-4 space-y-4">
            {/* Filters */}
            <div className="flex flex-wrap gap-3">
              <div className="flex-1 min-w-[200px]">
                <Input
                  placeholder="Search by description, barcode, or recipient..."
                  value={warehouseSearch}
                  onChange={(e) => setWarehouseSearch(e.target.value)}
                  className="h-9"
                />
              </div>
              <Select value={warehouseClientFilter} onValueChange={setWarehouseClientFilter}>
                <SelectTrigger className="w-[180px] h-9">
                  <SelectValue placeholder="All Clients" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Clients</SelectItem>
                  {clients.map(c => (
                    <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            {/* Parcels Table */}
            <ScrollArea className="h-[400px] border rounded">
              {loadingWarehouseParcels ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-8 w-8 animate-spin text-[#6B633C]" />
                </div>
              ) : filteredWarehouseParcels.length === 0 ? (
                <p className="text-center text-gray-500 py-12">No available parcels found</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow className="bg-gray-50">
                      <TableHead className="w-[40px]">
                        <Checkbox
                          checked={selectedWarehouseParcels.size === filteredWarehouseParcels.length && filteredWarehouseParcels.length > 0}
                          onCheckedChange={(checked) => {
                            if (checked) {
                              setSelectedWarehouseParcels(new Set(filteredWarehouseParcels.map(p => p.id)));
                            } else {
                              setSelectedWarehouseParcels(new Set());
                            }
                          }}
                        />
                      </TableHead>
                      <TableHead>Client</TableHead>
                      <TableHead>Recipient</TableHead>
                      <TableHead>Description</TableHead>
                      <TableHead className="text-right">KG</TableHead>
                      <TableHead className="text-center">Dimensions</TableHead>
                      <TableHead className="text-right">Vol Wt</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredWarehouseParcels.map(parcel => {
                      const volWeight = calculateVolumetricWeight(parcel.length_cm, parcel.width_cm, parcel.height_cm);
                      return (
                        <TableRow 
                          key={parcel.id}
                          className={cn(selectedWarehouseParcels.has(parcel.id) && "bg-[#6B633C]/5")}
                        >
                          <TableCell>
                            <Checkbox
                              checked={selectedWarehouseParcels.has(parcel.id)}
                              onCheckedChange={(checked) => {
                                const newSet = new Set(selectedWarehouseParcels);
                                if (checked) newSet.add(parcel.id);
                                else newSet.delete(parcel.id);
                                setSelectedWarehouseParcels(newSet);
                              }}
                            />
                          </TableCell>
                          <TableCell className="text-sm max-w-[100px] truncate" title={parcel.client_name}>
                            {parcel.client_name || '-'}
                          </TableCell>
                          <TableCell className="text-sm max-w-[100px] truncate" title={parcel.recipient}>
                            {parcel.recipient || '-'}
                          </TableCell>
                          <TableCell className="text-sm max-w-[150px] truncate" title={parcel.description}>
                            {parcel.description || '-'}
                          </TableCell>
                          <TableCell className="text-right font-mono text-sm">
                            {parcel.total_weight?.toFixed(2) || '-'}
                          </TableCell>
                          <TableCell className="text-center font-mono text-xs">
                            {formatDimensions(parcel.length_cm, parcel.width_cm, parcel.height_cm)}
                          </TableCell>
                          <TableCell className="text-right font-mono text-sm">
                            {volWeight ? volWeight.toFixed(2) : '-'}
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline" className="text-xs capitalize">
                              {parcel.status}
                            </Badge>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              )}
            </ScrollArea>
            
            {/* Summary */}
            <div className="text-sm text-gray-600">
              Showing {filteredWarehouseParcels.length} parcel(s) • {selectedWarehouseParcels.size} selected
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setWarehouseDialogOpen(false)}>Cancel</Button>
            <Button 
              onClick={addSelectedWarehouseParcels} 
              disabled={selectedWarehouseParcels.size === 0}
              className="bg-[#6B633C] hover:bg-[#5a5332]"
            >
              Add {selectedWarehouseParcels.size} Parcel(s)
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default InvoiceEditor;
