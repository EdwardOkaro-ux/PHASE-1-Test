import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { Layout } from '../components/Layout';
import { InvoiceEditor } from '../components/InvoiceEditor';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Checkbox } from '../components/ui/checkbox';
import { Switch } from '../components/ui/switch';
import { ScrollArea } from '../components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '../components/ui/dialog';
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '../components/ui/dropdown-menu';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';
import { 
  Search, Mail, Download, ChevronDown, ChevronRight, MoreVertical,
  FileText, Users, AlertTriangle, Receipt, CheckCircle, Clock,
  AlertCircle, Send, Loader2, X, MessageCircle
} from 'lucide-react';
import { format } from 'date-fns';
import { cn } from '../lib/utils';

const API = `${window.location.origin}/api`;

// Default exchange rate
const DEFAULT_KES_RATE = 6.67;

// Format currency with conversion
const formatCurrency = (amount, currency = 'ZAR', exchangeRate = DEFAULT_KES_RATE) => {
  const num = parseFloat(amount) || 0;
  if (currency === 'KES') {
    const kesAmount = num * exchangeRate;
    return 'KES ' + kesAmount.toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  return 'R ' + num.toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

// Status badge config
const statusConfig = {
  draft: { bg: 'bg-gray-100', text: 'text-gray-700', label: 'Unpaid' },
  sent: { bg: 'bg-gray-100', text: 'text-gray-700', label: 'Unpaid' },
  paid: { bg: 'bg-green-100', text: 'text-green-700', label: 'Paid ✓' },
  partial: { bg: 'bg-yellow-100', text: 'text-yellow-700', label: 'Partial' },
  overdue: { bg: 'bg-red-100', text: 'text-red-700', label: 'Overdue' }
};

// Row color based on status
const getRowColor = (status) => {
  switch (status) {
    case 'paid': return 'bg-green-50/50';
    case 'partial': return 'bg-yellow-50/50';
    case 'overdue': return 'bg-red-50/50';
    default: return '';
  }
};

// Overdue row color based on days
const getOverdueColor = (days) => {
  if (days > 30) return 'bg-red-100';
  if (days > 14) return 'bg-orange-100';
  return 'bg-yellow-50';
};

export function Finance() {
  const [activeTab, setActiveTab] = useState('statements');
  const [loading, setLoading] = useState(true);
  
  // Currency display toggle
  const [displayCurrency, setDisplayCurrency] = useState('ZAR');
  const [exchangeRate, setExchangeRate] = useState(DEFAULT_KES_RATE);
  
  // Client Statements state
  const [statements, setStatements] = useState([]);
  const [tripColumns, setTripColumns] = useState([]);
  const [statementsSummary, setStatementsSummary] = useState({});
  const [statementsSearch, setStatementsSearch] = useState('');
  const [expandedClients, setExpandedClients] = useState({});
  const [clientInvoices, setClientInvoices] = useState({});
  
  // Trip Worksheets state
  const [trips, setTrips] = useState([]);
  const [selectedTripId, setSelectedTripId] = useState('');
  const [worksheetData, setWorksheetData] = useState(null);
  const [selectedInvoices, setSelectedInvoices] = useState([]);
  
  // Overdue state
  const [overdueData, setOverdueData] = useState({ invoices: [], total_overdue: 0, count: 0 });
  const [selectedOverdue, setSelectedOverdue] = useState([]);
  
  // Email modal state
  const [emailModalOpen, setEmailModalOpen] = useState(false);
  const [emailData, setEmailData] = useState({
    to: '',
    subject: '',
    body: '',
    invoiceId: null,
    invoiceNumber: ''
  });
  const [sendingEmail, setSendingEmail] = useState(false);
  
  // WhatsApp sending state
  const [whatsappSending, setWhatsappSending] = useState(false);
  const [whatsappQueue, setWhatsappQueue] = useState([]);

  // Fetch exchange rates from settings
  useEffect(() => {
    const fetchExchangeRate = async () => {
      try {
        const response = await axios.get(`${API}/settings/currencies`, { withCredentials: true });
        if (response.data?.currencies) {
          const kesCurrency = response.data.currencies.find(c => c.code === 'KES');
          if (kesCurrency?.exchange_rate) {
            setExchangeRate(kesCurrency.exchange_rate);
          }
        }
      } catch (error) {
        console.error('Failed to fetch exchange rates:', error);
      }
    };
    fetchExchangeRate();
  }, []);

  // Helper for currency formatting with current toggle
  const fmtCurrency = (amount) => formatCurrency(amount, displayCurrency, exchangeRate);

  // Fetch data on mount
  useEffect(() => {
    fetchTrips();
    fetchStatements();
    fetchOverdue();
  }, []);

  // Fetch trips list
  const fetchTrips = async () => {
    try {
      const response = await axios.get(`${API}/trips`, { withCredentials: true });
      setTrips(response.data || []);
      if (response.data?.length > 0) {
        setSelectedTripId(response.data[0].id);
      }
    } catch (error) {
      console.error('Failed to fetch trips:', error);
    }
  };

  // Fetch client statements
  const fetchStatements = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/finance/client-statements`, { withCredentials: true });
      setStatements(response.data.statements || []);
      setTripColumns(response.data.trip_columns || []);
      setStatementsSummary(response.data.summary || {});
    } catch (error) {
      console.error('Failed to fetch statements:', error);
      toast.error('Failed to load client statements');
    } finally {
      setLoading(false);
    }
  };

  // Fetch worksheet for selected trip
  const fetchWorksheet = useCallback(async (tripId) => {
    if (!tripId) return;
    try {
      const response = await axios.get(`${API}/finance/trip-worksheet/${tripId}`, { withCredentials: true });
      setWorksheetData(response.data);
      setSelectedInvoices([]);
    } catch (error) {
      console.error('Failed to fetch worksheet:', error);
      toast.error('Failed to load trip worksheet');
    }
  }, []);

  // Fetch overdue invoices
  const fetchOverdue = async () => {
    try {
      const response = await axios.get(`${API}/finance/overdue`, { withCredentials: true });
      setOverdueData(response.data);
    } catch (error) {
      console.error('Failed to fetch overdue:', error);
    }
  };

  // Fetch worksheet when trip changes
  useEffect(() => {
    if (selectedTripId && activeTab === 'worksheets') {
      fetchWorksheet(selectedTripId);
    }
  }, [selectedTripId, activeTab, fetchWorksheet]);

  // Toggle client row expansion
  const toggleClientExpand = async (clientId) => {
    if (expandedClients[clientId]) {
      setExpandedClients(prev => ({ ...prev, [clientId]: false }));
    } else {
      // Fetch invoices for this client if not cached
      if (!clientInvoices[clientId]) {
        try {
          const response = await axios.get(
            `${API}/finance/client-statements/${clientId}/invoices`,
            { withCredentials: true }
          );
          setClientInvoices(prev => ({ ...prev, [clientId]: response.data }));
        } catch (error) {
          console.error('Failed to fetch client invoices:', error);
        }
      }
      setExpandedClients(prev => ({ ...prev, [clientId]: true }));
    }
  };

  // Handle invoice selection for batch actions
  const toggleInvoiceSelection = (invoiceId) => {
    setSelectedInvoices(prev => 
      prev.includes(invoiceId) 
        ? prev.filter(id => id !== invoiceId)
        : [...prev, invoiceId]
    );
  };

  const toggleAllInvoices = () => {
    if (!worksheetData?.invoices) return;
    if (selectedInvoices.length === worksheetData.invoices.length) {
      setSelectedInvoices([]);
    } else {
      setSelectedInvoices(worksheetData.invoices.map(inv => inv.id));
    }
  };

  // Open email modal
  const openEmailModal = (invoice, isReminder = false) => {
    const subject = isReminder 
      ? `REMINDER: Invoice ${invoice.invoice_number || invoice.invoiceNumber} is overdue`
      : `Invoice ${invoice.invoice_number || invoice.invoiceNumber} from Servex Holdings`;
    
    const body = isReminder
      ? `Dear ${invoice.client_name},

REMINDER: Invoice ${invoice.invoice_number || invoice.invoiceNumber} is ${invoice.days_overdue || 0} days overdue.

Original due date: ${invoice.due_date ? format(new Date(invoice.due_date), 'dd MMM yyyy') : 'N/A'}
Amount outstanding: ${fmtCurrency(invoice.outstanding)}

Please remit payment urgently.

Payment Details:
FNB Account: 63112859666
Reference: ${invoice.invoice_number || invoice.invoiceNumber}

Thank you,
Servex Holdings`
      : `Dear ${invoice.client_name},

Please find attached Invoice ${invoice.invoice_number || invoice.invoiceNumber} for ${fmtCurrency(invoice.total_amount || invoice.total)}.

Due Date: ${invoice.due_date ? format(new Date(invoice.due_date), 'dd MMM yyyy') : 'N/A'}
Amount Outstanding: ${fmtCurrency(invoice.outstanding)}

Payment Details:
FNB Account: 63112859666
Reference: ${invoice.invoice_number || invoice.invoiceNumber}

Thank you,
Servex Holdings`;

    setEmailData({
      to: invoice.client_email || '',
      subject,
      body,
      invoiceId: invoice.id,
      invoiceNumber: invoice.invoice_number || invoice.invoiceNumber
    });
    setEmailModalOpen(true);
  };

  // Send email
  const handleSendEmail = async () => {
    if (!emailData.to || !emailData.invoiceId) {
      toast.error('Email address is required');
      return;
    }

    setSendingEmail(true);
    try {
      await axios.post(
        `${API}/invoices/${emailData.invoiceId}/send-email`,
        {
          to: emailData.to,
          subject: emailData.subject,
          body: emailData.body,
          attach_pdf: true
        },
        { withCredentials: true }
      );
      toast.success(`Email logged for ${emailData.to}`);
      setEmailModalOpen(false);
    } catch (error) {
      toast.error('Failed to send email');
    } finally {
      setSendingEmail(false);
    }
  };

  // WhatsApp bulk send - queue messages sequentially
  const handleWhatsAppBulkSend = async (invoices, messageType = 'overdue') => {
    // Filter invoices with WhatsApp numbers
    const withWhatsApp = invoices.filter(inv => {
      const whatsapp = inv.client_whatsapp || inv.whatsapp;
      return whatsapp && whatsapp.trim();
    });
    
    const withoutWhatsApp = invoices.filter(inv => {
      const whatsapp = inv.client_whatsapp || inv.whatsapp;
      return !whatsapp || !whatsapp.trim();
    });

    if (withoutWhatsApp.length > 0) {
      const names = withoutWhatsApp.map(inv => inv.client_name).slice(0, 3).join(', ');
      const more = withoutWhatsApp.length > 3 ? ` and ${withoutWhatsApp.length - 3} more` : '';
      toast.warning(`No WhatsApp number for: ${names}${more}`);
    }

    if (withWhatsApp.length === 0) {
      toast.error('No clients with WhatsApp numbers selected');
      return;
    }

    setWhatsappSending(true);
    toast.info(`Sending ${withWhatsApp.length} WhatsApp message(s)...`);

    // Process sequentially with a delay
    for (let i = 0; i < withWhatsApp.length; i++) {
      const inv = withWhatsApp[i];
      const whatsapp = (inv.client_whatsapp || inv.whatsapp || '').replace(/[^\d+]/g, '');
      
      let message;
      if (messageType === 'overdue') {
        message = `Hi ${inv.client_name}, your invoice ${inv.invoice_number} for ${fmtCurrency(inv.outstanding || inv.total_amount)} is overdue. Please arrange payment.`;
      } else {
        message = `Hi ${inv.client_name}, your trip ${inv.trip_number || ''} worksheet totaling ${fmtCurrency(inv.total_amount || inv.outstanding)} is ready. Please review.`;
      }

      // Open WhatsApp Web
      const url = `https://wa.me/${whatsapp}?text=${encodeURIComponent(message)}`;
      window.open(url, '_blank');

      // Log the WhatsApp send
      try {
        await axios.post(`${API}/invoices/${inv.id}/log-whatsapp`, {
          to_number: whatsapp,
          message: message
        }, { withCredentials: true });
      } catch (error) {
        console.error('Failed to log WhatsApp:', error);
      }

      // Wait 2 seconds between each to allow user to send
      if (i < withWhatsApp.length - 1) {
        await new Promise(resolve => setTimeout(resolve, 2000));
      }
    }

    setWhatsappSending(false);
    toast.success(`Opened ${withWhatsApp.length} WhatsApp conversation(s)`);
  };

  // Download PDF
  const handleDownloadPdf = async (invoiceId) => {
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
    } catch (error) {
      toast.error('Failed to download PDF');
    }
  };

  // Filter statements by search
  const filteredStatements = statements.filter(s => 
    s.client_name.toLowerCase().includes(statementsSearch.toLowerCase())
  );

  return (
    <Layout>
      <div className="space-y-6" data-testid="finance-page">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-[#3C3F42]">Finance</h1>
            <p className="text-gray-500 text-sm">Manage invoices, statements, and payments</p>
          </div>
          
          {/* Currency Toggle - Global for all tabs */}
          <div className="flex items-center gap-3 bg-white border rounded-lg px-4 py-2" data-testid="currency-toggle">
            <span className={cn("text-sm font-medium transition-colors", displayCurrency === 'ZAR' ? "text-[#6B633C]" : "text-gray-400")}>
              ZAR
            </span>
            <Switch
              checked={displayCurrency === 'KES'}
              onCheckedChange={(checked) => setDisplayCurrency(checked ? 'KES' : 'ZAR')}
              data-testid="currency-switch"
            />
            <span className={cn("text-sm font-medium transition-colors", displayCurrency === 'KES' ? "text-[#6B633C]" : "text-gray-400")}>
              KES
            </span>
            <span className="text-xs text-muted-foreground ml-2">
              (1 ZAR = {exchangeRate} KES)
            </span>
          </div>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-4 bg-gray-100 p-1 rounded-lg">
            <TabsTrigger 
              value="statements" 
              className="data-[state=active]:bg-white data-[state=active]:text-[#6B633C] data-[state=active]:font-semibold data-[state=active]:border-b-2 data-[state=active]:border-[#6B633C]"
              data-testid="tab-statements"
            >
              <Users className="h-4 w-4 mr-2" />
              Client Statements
            </TabsTrigger>
            <TabsTrigger 
              value="worksheets"
              className="data-[state=active]:bg-white data-[state=active]:text-[#6B633C] data-[state=active]:font-semibold data-[state=active]:border-b-2 data-[state=active]:border-[#6B633C]"
              data-testid="tab-worksheets"
            >
              <FileText className="h-4 w-4 mr-2" />
              Trip Worksheets
            </TabsTrigger>
            <TabsTrigger 
              value="overdue"
              className="data-[state=active]:bg-white data-[state=active]:text-[#6B633C] data-[state=active]:font-semibold data-[state=active]:border-b-2 data-[state=active]:border-[#6B633C]"
              data-testid="tab-overdue"
            >
              <AlertTriangle className="h-4 w-4 mr-2" />
              Overdue ({overdueData.count})
            </TabsTrigger>
            <TabsTrigger 
              value="invoices"
              className="data-[state=active]:bg-white data-[state=active]:text-[#6B633C] data-[state=active]:font-semibold data-[state=active]:border-b-2 data-[state=active]:border-[#6B633C]"
              data-testid="tab-invoices"
            >
              <Receipt className="h-4 w-4 mr-2" />
              Invoice Details
            </TabsTrigger>
          </TabsList>

          {/* ========== TAB 1: CLIENT STATEMENTS ========== */}
          <TabsContent value="statements" className="mt-6">
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <Card className="border border-gray-200">
                <CardContent className="pt-6">
                  <div className="text-sm text-gray-500">Total Outstanding</div>
                  <div className="text-2xl font-bold text-[#3C3F42]">
                    {fmtCurrency(statementsSummary.total_outstanding || 0)}
                  </div>
                </CardContent>
              </Card>
              <Card className="border border-gray-200">
                <CardContent className="pt-6">
                  <div className="text-sm text-gray-500">Clients with Debt</div>
                  <div className="text-2xl font-bold text-[#3C3F42]">
                    {statementsSummary.clients_with_debt || 0} clients
                  </div>
                </CardContent>
              </Card>
              <Card className="border border-gray-200">
                <CardContent className="pt-6">
                  <div className="text-sm text-gray-500">Overdue Amount</div>
                  <div className="text-2xl font-bold text-red-600">
                    {fmtCurrency(statementsSummary.overdue_amount || 0)}
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Search */}
            <div className="flex items-center gap-4 mb-4">
              <div className="relative flex-1 max-w-md">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  placeholder="Search clients..."
                  value={statementsSearch}
                  onChange={(e) => setStatementsSearch(e.target.value)}
                  className="pl-10"
                  data-testid="statements-search"
                />
              </div>
            </div>

            {/* Statements Table */}
            <Card className="border border-gray-200">
              <div className="overflow-x-auto">
                <Table className="w-full table-fixed">
                  <TableHeader>
                    <TableRow className="bg-[#6B633C]">
                      <TableHead className="text-white font-semibold w-[4%]"></TableHead>
                      <TableHead className="text-white font-semibold w-[22%]">Client Name</TableHead>
                      <TableHead className="text-white font-semibold text-right w-[16%]">Total Outstanding</TableHead>
                      {tripColumns.map(trip => (
                        <TableHead key={trip} className="text-white font-semibold text-right" style={{ width: `${Math.floor(50 / Math.max(tripColumns.length, 1))}%` }}>
                          {trip}
                        </TableHead>
                      ))}
                      <TableHead className="text-white font-semibold w-[6%]">⋮</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {loading ? (
                      <TableRow>
                        <TableCell colSpan={tripColumns.length + 4} className="text-center py-8">
                          <Loader2 className="h-6 w-6 animate-spin mx-auto text-gray-400" />
                        </TableCell>
                      </TableRow>
                    ) : filteredStatements.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={tripColumns.length + 4} className="text-center py-8 text-gray-500">
                          No outstanding balances found
                        </TableCell>
                      </TableRow>
                    ) : (
                      filteredStatements.map((statement, index) => (
                        <React.Fragment key={statement.client_id}>
                          <TableRow 
                            className={cn(
                              "border-b border-gray-100 cursor-pointer hover:bg-gray-50",
                              index % 2 === 1 && "bg-gray-50/50"
                            )}
                            onClick={() => toggleClientExpand(statement.client_id)}
                          >
                            <TableCell>
                              <Button variant="ghost" size="sm" className="p-0 h-6 w-6">
                                {expandedClients[statement.client_id] ? (
                                  <ChevronDown className="h-4 w-4" />
                                ) : (
                                  <ChevronRight className="h-4 w-4" />
                                )}
                              </Button>
                            </TableCell>
                            <TableCell className="font-medium">{statement.client_name}</TableCell>
                            <TableCell className={cn(
                              "text-right font-bold font-mono",
                              statement.total_outstanding > 10000 && "text-red-600"
                            )}>
                              {fmtCurrency(statement.total_outstanding)}
                            </TableCell>
                            {tripColumns.map(trip => (
                              <TableCell key={trip} className="text-right font-mono text-gray-600">
                                {statement.trip_amounts[trip] 
                                  ? fmtCurrency(statement.trip_amounts[trip])
                                  : '-'
                                }
                              </TableCell>
                            ))}
                            <TableCell>
                              <DropdownMenu>
                                <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                                  <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                                    <MoreVertical className="h-4 w-4" />
                                  </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="end">
                                  <DropdownMenuItem onClick={(e) => {
                                    e.stopPropagation();
                                    openEmailModal({ 
                                      client_name: statement.client_name,
                                      client_email: statement.client_email,
                                      invoice_number: `STMT-${statement.client_id.slice(-6)}`,
                                      total_amount: statement.total_outstanding,
                                      outstanding: statement.total_outstanding,
                                      id: statement.client_id
                                    });
                                  }}>
                                    <Mail className="h-4 w-4 mr-2" /> Email Statement
                                  </DropdownMenuItem>
                                  <DropdownMenuItem onClick={(e) => {
                                    e.stopPropagation();
                                    toggleClientExpand(statement.client_id);
                                  }}>
                                    <FileText className="h-4 w-4 mr-2" /> View All Invoices
                                  </DropdownMenuItem>
                                </DropdownMenuContent>
                              </DropdownMenu>
                            </TableCell>
                          </TableRow>
                          {expandedClients[statement.client_id] && (
                            <TableRow key={`${statement.client_id}-expanded`} className="bg-gray-50">
                              <TableCell colSpan={tripColumns.length + 4} className="p-0">
                                <div className="p-4 border-t border-gray-200">
                                  <p className="text-sm font-medium mb-2">Unpaid Invoices</p>
                                  <Table>
                                    <TableHeader>
                                      <TableRow className="bg-gray-100">
                                        <TableHead className="text-xs">Invoice #</TableHead>
                                        <TableHead className="text-xs">Trip</TableHead>
                                        <TableHead className="text-xs text-right">Amount</TableHead>
                                        <TableHead className="text-xs">Due Date</TableHead>
                                        <TableHead className="text-xs">Status</TableHead>
                                        <TableHead className="text-xs"></TableHead>
                                      </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                      {(clientInvoices[statement.client_id] || []).map(inv => (
                                        <TableRow key={inv.id}>
                                          <TableCell className="text-sm">{inv.invoice_number}</TableCell>
                                          <TableCell className="text-sm">{inv.trip_number}</TableCell>
                                          <TableCell className="text-sm text-right font-mono">
                                            {fmtCurrency(inv.outstanding)}
                                          </TableCell>
                                          <TableCell className="text-sm">
                                            {inv.due_date ? format(new Date(inv.due_date), 'dd MMM yyyy') : '-'}
                                          </TableCell>
                                          <TableCell>
                                            <Badge className={cn(
                                              "text-xs",
                                              statusConfig[inv.status]?.bg,
                                              statusConfig[inv.status]?.text
                                            )}>
                                              {statusConfig[inv.status]?.label || inv.status}
                                            </Badge>
                                          </TableCell>
                                          <TableCell>
                                            <Button 
                                              variant="ghost" 
                                              size="sm"
                                              onClick={() => openEmailModal({
                                                ...inv,
                                                client_name: statement.client_name,
                                                client_email: statement.client_email
                                              })}
                                            >
                                              <Mail className="h-3 w-3" />
                                            </Button>
                                          </TableCell>
                                        </TableRow>
                                      ))}
                                    </TableBody>
                                  </Table>
                                </div>
                              </TableCell>
                            </TableRow>
                          )}
                        </React.Fragment>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            </Card>
          </TabsContent>

          {/* ========== TAB 2: TRIP WORKSHEETS ========== */}
          <TabsContent value="worksheets" className="mt-6">
            {/* Trip Selector */}
            <div className="flex items-center gap-4 mb-6">
              <Select value={selectedTripId} onValueChange={setSelectedTripId}>
                <SelectTrigger className="w-[300px]" data-testid="trip-selector">
                  <SelectValue placeholder="Select Trip" />
                </SelectTrigger>
                <SelectContent>
                  {trips.map(trip => (
                    <SelectItem key={trip.id} value={trip.id}>
                      {trip.trip_number} - {trip.route?.join(' → ') || 'No route'}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {worksheetData && (
              <>
                {/* Summary Cards */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                  <Card className="border border-gray-200">
                    <CardContent className="pt-6">
                      <div className="text-sm text-gray-500">Total Revenue</div>
                      <div className="text-xl font-bold text-[#3C3F42]">
                        {fmtCurrency(worksheetData.summary.total_revenue)}
                      </div>
                    </CardContent>
                  </Card>
                  <Card className="border border-gray-200">
                    <CardContent className="pt-6">
                      <div className="text-sm text-gray-500">Collected</div>
                      <div className="text-xl font-bold text-green-600">
                        {fmtCurrency(worksheetData.summary.total_collected)}
                        <span className="text-sm text-gray-500 ml-1">
                          ({worksheetData.summary.collection_percent}%)
                        </span>
                      </div>
                    </CardContent>
                  </Card>
                  <Card className="border border-gray-200">
                    <CardContent className="pt-6">
                      <div className="text-sm text-gray-500">Outstanding</div>
                      <div className="text-xl font-bold text-red-600">
                        {fmtCurrency(worksheetData.summary.total_outstanding)}
                      </div>
                    </CardContent>
                  </Card>
                  <Card className="border border-gray-200">
                    <CardContent className="pt-6">
                      <div className="text-sm text-gray-500">Invoices Paid</div>
                      <div className="text-xl font-bold text-[#3C3F42]">
                        {worksheetData.summary.invoices_paid} of {worksheetData.summary.invoices_total}
                      </div>
                    </CardContent>
                  </Card>
                </div>

                {/* Progress Bar */}
                <div className="mb-6">
                  <div className="w-full bg-gray-200 rounded-full h-3">
                    <div 
                      className="bg-[#6B633C] h-3 rounded-full transition-all duration-500"
                      style={{ width: `${worksheetData.summary.collection_percent}%` }}
                    />
                  </div>
                  <p className="text-sm text-gray-500 mt-1">
                    {worksheetData.summary.collection_percent}% collected
                  </p>
                </div>

                {/* Invoice Table */}
                <Card className="border border-gray-200">
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow className="bg-[#6B633C]">
                          <TableHead className="w-[40px]">
                            <Checkbox 
                              checked={selectedInvoices.length === worksheetData.invoices.length}
                              onCheckedChange={toggleAllInvoices}
                              className="border-white"
                            />
                          </TableHead>
                          <TableHead className="text-white font-semibold">Sender/Client</TableHead>
                          <TableHead className="text-white font-semibold">Invoice #</TableHead>
                          <TableHead className="text-white font-semibold">Recipient</TableHead>
                          <TableHead className="text-white font-semibold text-right">Weight (kg)</TableHead>
                          <TableHead className="text-white font-semibold text-right">Total</TableHead>
                          <TableHead className="text-white font-semibold text-right">Paid</TableHead>
                          <TableHead className="text-white font-semibold text-right">Outstanding</TableHead>
                          <TableHead className="text-white font-semibold text-center">Status</TableHead>
                          <TableHead className="text-white font-semibold w-[50px]"></TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {worksheetData.invoices.map((inv, index) => (
                          <TableRow 
                            key={inv.id}
                            className={cn(
                              "border-b border-gray-100",
                              getRowColor(inv.status),
                              index % 2 === 1 && !getRowColor(inv.status) && "bg-gray-50/50"
                            )}
                          >
                            <TableCell>
                              <Checkbox 
                                checked={selectedInvoices.includes(inv.id)}
                                onCheckedChange={() => toggleInvoiceSelection(inv.id)}
                              />
                            </TableCell>
                            <TableCell className="font-medium">{inv.client_name}</TableCell>
                            <TableCell className="font-mono text-sm">{inv.invoice_number}</TableCell>
                            <TableCell>{inv.recipient}</TableCell>
                            <TableCell className="text-right font-mono">{inv.weight_kg.toFixed(2)}</TableCell>
                            <TableCell className="text-right font-mono">{fmtCurrency(inv.total_amount)}</TableCell>
                            <TableCell className="text-right font-mono text-green-600">
                              {inv.paid_amount > 0 ? fmtCurrency(inv.paid_amount) : '-'}
                            </TableCell>
                            <TableCell className="text-right font-mono text-red-600">
                              {inv.outstanding > 0 ? fmtCurrency(inv.outstanding) : '-'}
                            </TableCell>
                            <TableCell className="text-center">
                              <Badge className={cn(
                                "text-xs px-3",
                                statusConfig[inv.status]?.bg,
                                statusConfig[inv.status]?.text
                              )}>
                                {statusConfig[inv.status]?.label || inv.status}
                              </Badge>
                            </TableCell>
                            <TableCell>
                              <Button 
                                variant="ghost" 
                                size="sm"
                                onClick={() => openEmailModal(inv)}
                                disabled={!inv.client_email}
                              >
                                <Mail className="h-4 w-4" />
                              </Button>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </Card>

                {/* Batch Actions */}
                {selectedInvoices.length > 0 && (
                  <div className="fixed bottom-6 left-1/2 transform -translate-x-1/2 bg-[#3C3F42] text-white px-6 py-3 rounded-lg shadow-lg flex items-center gap-4">
                    <span>{selectedInvoices.length} selected</span>
                    <Button 
                      variant="secondary" 
                      size="sm"
                      onClick={() => {
                        const selected = worksheetData.invoices.filter(inv => selectedInvoices.includes(inv.id));
                        handleWhatsAppBulkSend(selected, 'worksheet');
                      }}
                      disabled={whatsappSending}
                    >
                      <MessageCircle className="h-4 w-4 mr-2" /> WhatsApp Selected
                    </Button>
                    <Button 
                      variant="secondary" 
                      size="sm"
                      onClick={() => toast.info('Batch email feature coming soon')}
                    >
                      <Send className="h-4 w-4 mr-2" /> Email Selected
                    </Button>
                    <Button 
                      variant="secondary" 
                      size="sm"
                      onClick={() => toast.info('Export feature coming soon')}
                    >
                      <Download className="h-4 w-4 mr-2" /> Export PDF
                    </Button>
                  </div>
                )}
              </>
            )}
          </TabsContent>

          {/* ========== TAB 3: OVERDUE ========== */}
          <TabsContent value="overdue" className="mt-6">
            {/* Summary */}
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-lg font-semibold text-[#3C3F42]">
                  {overdueData.count} Overdue Invoice{overdueData.count !== 1 ? 's' : ''}
                </h2>
                <p className="text-sm text-gray-500">
                  Total outstanding: {fmtCurrency(overdueData.total_overdue)}
                </p>
              </div>
              <div className="flex gap-2">
                <Button 
                  variant="outline"
                  onClick={() => {
                    const selected = overdueData.invoices.filter(inv => selectedOverdue.includes(inv.id));
                    if (selected.length === 0) {
                      toast.error('Please select invoices to send WhatsApp');
                      return;
                    }
                    handleWhatsAppBulkSend(selected, 'overdue');
                  }}
                  disabled={selectedOverdue.length === 0 || whatsappSending}
                  data-testid="bulk-whatsapp-btn"
                >
                  {whatsappSending ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <MessageCircle className="h-4 w-4 mr-2" />}
                  WhatsApp Selected ({selectedOverdue.length})
                </Button>
                <Button 
                  variant="outline"
                  onClick={() => {
                    if (overdueData.invoices.length === 0) return;
                    handleWhatsAppBulkSend(overdueData.invoices, 'overdue');
                  }}
                  disabled={overdueData.invoices.length === 0 || whatsappSending}
                >
                  <Send className="h-4 w-4 mr-2" /> Send All Reminders
                </Button>
              </div>
            </div>

            {/* Overdue Table */}
            <Card className="border border-gray-200">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-[#6B633C]">
                      <TableHead className="w-[40px]">
                        <Checkbox 
                          checked={selectedOverdue.length === overdueData.invoices.length && overdueData.invoices.length > 0}
                          onCheckedChange={(checked) => {
                            if (checked) {
                              setSelectedOverdue(overdueData.invoices.map(inv => inv.id));
                            } else {
                              setSelectedOverdue([]);
                            }
                          }}
                          className="border-white"
                        />
                      </TableHead>
                      <TableHead className="text-white font-semibold">Client Name</TableHead>
                      <TableHead className="text-white font-semibold">Invoice #</TableHead>
                      <TableHead className="text-white font-semibold">Trip</TableHead>
                      <TableHead className="text-white font-semibold">Due Date</TableHead>
                      <TableHead className="text-white font-semibold text-center">Days Overdue</TableHead>
                      <TableHead className="text-white font-semibold text-right">Outstanding</TableHead>
                      <TableHead className="text-white font-semibold w-[140px]"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {overdueData.invoices.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={8} className="text-center py-8 text-gray-500">
                          <CheckCircle className="h-8 w-8 mx-auto mb-2 text-green-500" />
                          No overdue invoices!
                        </TableCell>
                      </TableRow>
                    ) : (
                      overdueData.invoices.map((inv) => (
                        <TableRow 
                          key={inv.id}
                          className={cn("border-b border-gray-100", getOverdueColor(inv.days_overdue))}
                        >
                          <TableCell>
                            <Checkbox 
                              checked={selectedOverdue.includes(inv.id)}
                              onCheckedChange={(checked) => {
                                if (checked) {
                                  setSelectedOverdue([...selectedOverdue, inv.id]);
                                } else {
                                  setSelectedOverdue(selectedOverdue.filter(id => id !== inv.id));
                                }
                              }}
                            />
                          </TableCell>
                          <TableCell className="font-medium">{inv.client_name}</TableCell>
                          <TableCell className="font-mono text-sm">{inv.invoice_number}</TableCell>
                          <TableCell>{inv.trip_number}</TableCell>
                          <TableCell>
                            {inv.due_date ? format(new Date(inv.due_date), 'dd MMM yyyy') : '-'}
                          </TableCell>
                          <TableCell className="text-center">
                            <Badge className={cn(
                              "text-xs",
                              inv.days_overdue > 30 ? "bg-red-600 text-white" :
                              inv.days_overdue > 14 ? "bg-orange-500 text-white" :
                              "bg-yellow-500 text-white"
                            )}>
                              {inv.days_overdue} days
                            </Badge>
                          </TableCell>
                          <TableCell className="text-right font-mono font-bold text-red-600">
                            {fmtCurrency(inv.outstanding)}
                          </TableCell>
                          <TableCell>
                            <div className="flex gap-1">
                              <Button 
                                variant="outline" 
                                size="sm"
                                onClick={() => openEmailModal(inv, true)}
                                disabled={!inv.client_email}
                              >
                                <Mail className="h-3 w-3" />
                              </Button>
                              <Button 
                                variant="outline" 
                                size="sm"
                                onClick={() => handleWhatsAppBulkSend([inv], 'overdue')}
                                disabled={!inv.client_whatsapp}
                                title={inv.client_whatsapp ? 'Send WhatsApp' : 'No WhatsApp number'}
                              >
                                <MessageCircle className="h-3 w-3" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            </Card>
          </TabsContent>

          {/* ========== TAB 4: INVOICE DETAILS ========== */}
          <TabsContent value="invoices" className="mt-6">
            <InvoiceEditor />
          </TabsContent>
        </Tabs>

        {/* Email Modal */}
        <Dialog open={emailModalOpen} onOpenChange={setEmailModalOpen}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Mail className="h-5 w-5" />
                Send Invoice Email
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div>
                <label className="text-sm font-medium">To:</label>
                <Input
                  value={emailData.to}
                  onChange={(e) => setEmailData(prev => ({ ...prev, to: e.target.value }))}
                  placeholder="client@email.com"
                  className="mt-1"
                />
                {!emailData.to && (
                  <p className="text-xs text-amber-600 mt-1">
                    ⚠️ No email on file for this client
                  </p>
                )}
              </div>
              <div>
                <label className="text-sm font-medium">Subject:</label>
                <Input
                  value={emailData.subject}
                  onChange={(e) => setEmailData(prev => ({ ...prev, subject: e.target.value }))}
                  className="mt-1"
                />
              </div>
              <div>
                <label className="text-sm font-medium">Message:</label>
                <Textarea
                  value={emailData.body}
                  onChange={(e) => setEmailData(prev => ({ ...prev, body: e.target.value }))}
                  rows={10}
                  className="mt-1 font-mono text-sm"
                />
              </div>
              <div className="bg-gray-50 p-3 rounded-lg">
                <p className="text-sm text-gray-600">
                  📎 Attachment: Invoice_{emailData.invoiceNumber}.pdf
                </p>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setEmailModalOpen(false)}>
                Cancel
              </Button>
              <Button 
                onClick={handleSendEmail}
                disabled={sendingEmail || !emailData.to}
                className="bg-[#6B633C] hover:bg-[#5a5332]"
              >
                {sendingEmail ? (
                  <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Sending...</>
                ) : (
                  <><Send className="h-4 w-4 mr-2" /> Send Email</>
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
}

export default Finance;
