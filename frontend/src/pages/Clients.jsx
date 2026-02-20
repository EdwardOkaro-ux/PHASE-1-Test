import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Layout } from '../components/Layout';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Skeleton } from '../components/ui/skeleton';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
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
import { toast } from 'sonner';
import { Plus, Search, MoreVertical, Edit, Trash2, DollarSign, Users, ArrowUpDown, Truck } from 'lucide-react';
import { cn } from '../lib/utils';

const API = `${window.location.origin}/api`;

const sortOptions = [
  { value: 'name-asc', label: 'Name A-Z' },
  { value: 'name-desc', label: 'Name Z-A' },
  { value: 'amount_owed-desc', label: 'Amount Owed (Highest)' },
  { value: 'total_spent-desc', label: 'Total Spent (Highest)' },
  { value: 'rate-desc', label: 'Rate (Highest)' },
  { value: 'created_at-desc', label: 'Newest First' },
  { value: 'created_at-asc', label: 'Oldest First' },
];

export function Clients() {
  const navigate = useNavigate();
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState('name-asc');
  const [tripFilter, setTripFilter] = useState('all');
  const [trips, setTrips] = useState([]);
  
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingClient, setEditingClient] = useState(null);
  const [ratesDialogOpen, setRatesDialogOpen] = useState(false);
  const [selectedClient, setSelectedClient] = useState(null);
  const [rates, setRates] = useState([]);
  
  const [formData, setFormData] = useState({
    name: '',
    phone: '',
    email: '',
    whatsapp: '',
    physical_address: '',
    billing_address: '',
    vat_number: '',
    payment_terms_days: 30,
    default_currency: 'ZAR'
  });
  
  const [rateForm, setRateForm] = useState({
    rate_type: 'per_kg',
    rate_value: 0,
    notes: ''
  });

  useEffect(() => {
    fetchClients();
    fetchTrips();
  }, [sortBy, tripFilter]);

  const fetchClients = async () => {
    setLoading(true);
    try {
      const [sortField, sortOrder] = sortBy.split('-');
      const params = new URLSearchParams({
        sort_by: sortField,
        sort_order: sortOrder
      });
      if (tripFilter && tripFilter !== 'all') {
        params.append('trip_id', tripFilter);
      }
      
      const response = await axios.get(`${API}/clients-with-stats?${params}`, { withCredentials: true });
      setClients(response.data);
    } catch (error) {
      toast.error('Failed to fetch clients');
    } finally {
      setLoading(false);
    }
  };

  const fetchTrips = async () => {
    try {
      const response = await axios.get(`${API}/trips`, { withCredentials: true });
      setTrips(response.data);
    } catch (error) {
      console.error('Failed to fetch trips');
    }
  };

  const fetchRates = async (clientId) => {
    try {
      const response = await axios.get(`${API}/clients/${clientId}/rates`, { withCredentials: true });
      setRates(response.data);
    } catch (error) {
      toast.error('Failed to fetch rates');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingClient) {
        await axios.put(`${API}/clients/${editingClient.id}`, formData, { withCredentials: true });
        toast.success('Client updated');
      } else {
        await axios.post(`${API}/clients`, formData, { withCredentials: true });
        toast.success('Client created');
      }
      setDialogOpen(false);
      resetForm();
      fetchClients();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save client');
    }
  };

  const handleDelete = async (clientId) => {
    if (!window.confirm('Are you sure you want to delete this client?')) return;
    try {
      await axios.delete(`${API}/clients/${clientId}`, { withCredentials: true });
      toast.success('Client deleted');
      fetchClients();
    } catch (error) {
      toast.error('Failed to delete client');
    }
  };

  const handleAddRate = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/clients/${selectedClient.id}/rates`, rateForm, { withCredentials: true });
      toast.success('Rate added');
      fetchRates(selectedClient.id);
      fetchClients(); // Refresh to update rate column
      setRateForm({ rate_type: 'per_kg', rate_value: 0, notes: '' });
    } catch (error) {
      toast.error('Failed to add rate');
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      phone: '',
      email: '',
      whatsapp: '',
      physical_address: '',
      billing_address: '',
      vat_number: '',
      payment_terms_days: 30,
      default_currency: 'ZAR'
    });
    setEditingClient(null);
  };

  const openEdit = (client) => {
    setEditingClient(client);
    setFormData({
      name: client.name,
      phone: client.phone || '',
      email: client.email || '',
      whatsapp: client.whatsapp || '',
      physical_address: client.physical_address || '',
      billing_address: client.billing_address || '',
      vat_number: client.vat_number || '',
      payment_terms_days: client.payment_terms_days,
      default_currency: client.default_currency
    });
    setDialogOpen(true);
  };

  const openRates = (client) => {
    setSelectedClient(client);
    fetchRates(client.id);
    setRatesDialogOpen(true);
  };

  const filteredClients = clients.filter(client =>
    client.name.toLowerCase().includes(search.toLowerCase()) ||
    client.email?.toLowerCase().includes(search.toLowerCase()) ||
    client.phone?.includes(search)
  );

  const formatRate = (client) => {
    if (!client.current_rate) return '-';
    const rateType = client.rate_type || 'per_kg';
    if (rateType === 'per_kg') {
      return `R${client.current_rate}/kg`;
    } else if (rateType === 'per_cbm') {
      return `R${client.current_rate}/cbm`;
    } else if (rateType === 'flat_rate') {
      return `R${client.current_rate} flat`;
    }
    return `R${client.current_rate}`;
  };

  const formatCurrency = (amount, currency = 'ZAR') => {
    if (amount === 0) return '-';
    return `${currency} ${amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  return (
    <Layout>
      <div className="space-y-6" data-testid="clients-page">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="font-heading text-2xl sm:text-3xl font-bold">Clients</h1>
            <p className="text-muted-foreground mt-1">Manage your client database</p>
          </div>
          <Dialog open={dialogOpen} onOpenChange={(open) => { setDialogOpen(open); if (!open) resetForm(); }}>
            <DialogTrigger asChild>
              <Button data-testid="add-client-btn">
                <Plus className="h-4 w-4 mr-2" />
                Add Client
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-md">
              <DialogHeader>
                <DialogTitle>{editingClient ? 'Edit Client' : 'Add New Client'}</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Client Name *</Label>
                  <Input
                    id="name"
                    placeholder="Enter client name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    required
                    data-testid="client-name-input"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="phone">Phone</Label>
                    <Input
                      id="phone"
                      placeholder="+27..."
                      value={formData.phone}
                      onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                      data-testid="client-phone-input"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="email">Email</Label>
                    <Input
                      id="email"
                      type="email"
                      placeholder="client@email.com"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      data-testid="client-email-input"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="whatsapp">WhatsApp</Label>
                  <Input
                    id="whatsapp"
                    placeholder="+27..."
                    value={formData.whatsapp}
                    onChange={(e) => setFormData({ ...formData, whatsapp: e.target.value })}
                    data-testid="client-whatsapp-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="vat_number">VAT Number</Label>
                  <Input
                    id="vat_number"
                    placeholder="VAT number..."
                    value={formData.vat_number}
                    onChange={(e) => setFormData({ ...formData, vat_number: e.target.value })}
                    data-testid="client-vat-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="physical_address">Physical Address</Label>
                  <Input
                    id="physical_address"
                    placeholder="Physical address..."
                    value={formData.physical_address}
                    onChange={(e) => setFormData({ ...formData, physical_address: e.target.value })}
                    data-testid="client-physical-address-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="billing_address">Billing Address</Label>
                  <Input
                    id="billing_address"
                    placeholder="Billing address (if different)..."
                    value={formData.billing_address}
                    onChange={(e) => setFormData({ ...formData, billing_address: e.target.value })}
                    data-testid="client-billing-address-input"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="payment_terms">Payment Terms (days)</Label>
                    <Input
                      id="payment_terms"
                      type="number"
                      value={formData.payment_terms_days}
                      onChange={(e) => setFormData({ ...formData, payment_terms_days: parseInt(e.target.value) || 30 })}
                      data-testid="client-terms-input"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="currency">Default Currency</Label>
                    <Select
                      value={formData.default_currency}
                      onValueChange={(value) => setFormData({ ...formData, default_currency: value })}
                    >
                      <SelectTrigger data-testid="client-currency-select">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="ZAR">ZAR (South African Rand)</SelectItem>
                        <SelectItem value="USD">USD (US Dollar)</SelectItem>
                        <SelectItem value="NGN">NGN (Nigerian Naira)</SelectItem>
                        <SelectItem value="KES">KES (Kenyan Shilling)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <DialogFooter>
                  <Button type="submit" data-testid="save-client-btn">
                    {editingClient ? 'Update' : 'Create'} Client
                  </Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        {/* Search and Filters */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-col lg:flex-row gap-3">
              {/* Search */}
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search clients..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-9"
                  data-testid="client-search-input"
                />
              </div>
              
              {/* Trip Filter */}
              <Select value={tripFilter} onValueChange={setTripFilter}>
                <SelectTrigger className="w-[200px]" data-testid="trip-filter-select">
                  <Truck className="h-4 w-4 mr-2" />
                  <SelectValue placeholder="Filter by Trip" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Clients</SelectItem>
                  {trips.map(trip => (
                    <SelectItem key={trip.id} value={trip.id}>
                      {trip.trip_number}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              
              {/* Sort */}
              <Select value={sortBy} onValueChange={setSortBy}>
                <SelectTrigger className="w-[200px]" data-testid="sort-select">
                  <ArrowUpDown className="h-4 w-4 mr-2" />
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {sortOptions.map(opt => (
                    <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Clients Table */}
        <Card>
          <CardContent className="p-0">
            {loading ? (
              <div className="p-6 space-y-3">
                {[1, 2, 3, 4, 5].map((i) => (
                  <Skeleton key={i} className="h-12 w-full" />
                ))}
              </div>
            ) : filteredClients.length > 0 ? (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="pl-6">Name</TableHead>
                      <TableHead className="hidden sm:table-cell">Contact</TableHead>
                      <TableHead className="hidden md:table-cell text-right">Rate</TableHead>
                      <TableHead className="hidden lg:table-cell text-right">Amount Owed</TableHead>
                      <TableHead className="hidden lg:table-cell text-right">Total Spent</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right pr-6">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredClients.map((client) => (
                      <TableRow key={client.id} data-testid={`client-row-${client.id}`}>
                        <TableCell className="pl-6">
                          <div>
                            <p className="font-medium">{client.name}</p>
                            <p className="text-sm text-muted-foreground sm:hidden">{client.phone}</p>
                          </div>
                        </TableCell>
                        <TableCell className="hidden sm:table-cell">
                          <div className="text-sm">
                            <p>{client.phone || '-'}</p>
                            <p className="text-muted-foreground">{client.email || '-'}</p>
                          </div>
                        </TableCell>
                        <TableCell className="hidden md:table-cell text-right">
                          <span className="font-mono text-sm">
                            {formatRate(client)}
                          </span>
                        </TableCell>
                        <TableCell className="hidden lg:table-cell text-right">
                          <span className={cn(
                            "font-mono text-sm",
                            client.amount_owed > 0 && "text-amber-600 font-medium"
                          )}>
                            {formatCurrency(client.amount_owed, client.default_currency)}
                          </span>
                        </TableCell>
                        <TableCell className="hidden lg:table-cell text-right">
                          <span className="font-mono text-sm text-muted-foreground">
                            {formatCurrency(client.total_spent, client.default_currency)}
                          </span>
                        </TableCell>
                        <TableCell>
                          <Badge className={client.status === 'active' ? 'bg-green-100 text-green-700 border-green-200' : 'bg-gray-100 text-gray-600 border-gray-200'}>
                            {client.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right pr-6">
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="icon" data-testid={`client-menu-${client.id}`}>
                                <MoreVertical className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem onClick={() => openEdit(client)}>
                                <Edit className="h-4 w-4 mr-2" />
                                Edit
                              </DropdownMenuItem>
                              <DropdownMenuItem onClick={() => openRates(client)}>
                                <DollarSign className="h-4 w-4 mr-2" />
                                Manage Rates
                              </DropdownMenuItem>
                              <DropdownMenuItem
                                onClick={() => handleDelete(client.id)}
                                className="text-destructive"
                              >
                                <Trash2 className="h-4 w-4 mr-2" />
                                Delete
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            ) : (
              <div className="text-center py-12 text-muted-foreground">
                <Users className="h-12 w-12 mx-auto mb-3 opacity-50" />
                <p>No clients found</p>
                <Button
                  variant="link"
                  onClick={() => setDialogOpen(true)}
                  className="mt-2"
                >
                  Add your first client
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Rates Dialog */}
        <Dialog open={ratesDialogOpen} onOpenChange={setRatesDialogOpen}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>Rates for {selectedClient?.name}</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              {/* Add Rate Form */}
              <form onSubmit={handleAddRate} className="space-y-4 p-4 bg-muted/50 rounded-lg">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Rate Type</Label>
                    <Select
                      value={rateForm.rate_type}
                      onValueChange={(value) => setRateForm({ ...rateForm, rate_type: value })}
                    >
                      <SelectTrigger data-testid="rate-type-select">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="per_kg">Per KG</SelectItem>
                        <SelectItem value="per_cbm">Per CBM</SelectItem>
                        <SelectItem value="flat_rate">Flat Rate</SelectItem>
                        <SelectItem value="custom">Custom</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Rate Value</Label>
                    <Input
                      type="number"
                      step="0.01"
                      value={rateForm.rate_value}
                      onChange={(e) => setRateForm({ ...rateForm, rate_value: parseFloat(e.target.value) || 0 })}
                      data-testid="rate-value-input"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Notes</Label>
                  <Input
                    value={rateForm.notes}
                    onChange={(e) => setRateForm({ ...rateForm, notes: e.target.value })}
                    placeholder="Optional notes..."
                    data-testid="rate-notes-input"
                  />
                </div>
                <Button type="submit" size="sm" data-testid="add-rate-btn">
                  <Plus className="h-4 w-4 mr-2" />
                  Add Rate
                </Button>
              </form>

              {/* Rates List */}
              <div className="space-y-2">
                <h4 className="font-medium">Current Rates</h4>
                {rates.length > 0 ? (
                  <div className="space-y-2">
                    {rates.map((rate) => (
                      <div
                        key={rate.id}
                        className="flex items-center justify-between p-3 bg-card border rounded-lg"
                        data-testid={`rate-${rate.id}`}
                      >
                        <div>
                          <Badge variant="outline" className="mb-1">
                            {rate.rate_type.replace('_', ' ')}
                          </Badge>
                          <p className="font-mono font-semibold">
                            {selectedClient?.default_currency} {rate.rate_value}
                          </p>
                          {rate.notes && (
                            <p className="text-sm text-muted-foreground">{rate.notes}</p>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground">
                          From: {rate.effective_from}
                        </p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">No rates configured</p>
                )}
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
}
