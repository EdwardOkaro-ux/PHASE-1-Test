import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Layout } from '../components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Label } from '../components/ui/label';
import { Checkbox } from '../components/ui/checkbox';
import { Tabs, TabsList, TabsTrigger } from '../components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import { toast } from 'sonner';
import { 
  Package, Truck, Warehouse as WarehouseIcon, ScanLine, Lock, Unlock, 
  RefreshCw, Loader2, ArrowRight, ArrowLeft, Download
} from 'lucide-react';

const API = `${window.location.origin}/api`;

export function LoadingStaging() {
  const [selectedTrip, setSelectedTrip] = useState(null);
  const [selectedWarehouse, setSelectedWarehouse] = useState('all');
  const [trips, setTrips] = useState([]);
  const [warehouses, setWarehouses] = useState([]);
  
  // Mode: 'loading' or 'unloading'
  const [mode, setMode] = useState('loading');
  
  // Parcel lists
  const [warehouseParcels, setWarehouseParcels] = useState([]);
  const [truckParcels, setTruckParcels] = useState([]);
  
  // For unloading mode - parcels that are in_transit
  const [inTransitParcels, setInTransitParcels] = useState([]);
  const [arrivedParcels, setArrivedParcels] = useState([]);
  
  // Selection for manual moves
  const [selectedWarehouseParcels, setSelectedWarehouseParcels] = useState(new Set());
  const [selectedTruckParcels, setSelectedTruckParcels] = useState(new Set());
  const [selectedInTransitParcels, setSelectedInTransitParcels] = useState(new Set());
  const [selectedArrivedParcels, setSelectedArrivedParcels] = useState(new Set());
  
  // Barcode scanner
  const [barcodeInput, setBarcodeInput] = useState('');
  const barcodeRef = useRef(null);
  
  const [loading, setLoading] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [moving, setMoving] = useState(false);

  useEffect(() => {
    fetchTrips();
    fetchWarehouses();
  }, []);

  useEffect(() => {
    if (selectedTrip) {
      fetchParcels();
    }
  }, [selectedTrip, selectedWarehouse, mode]);

  // Auto-focus barcode input
  useEffect(() => {
    if (barcodeRef.current) {
      barcodeRef.current.focus();
    }
  }, [selectedTrip]);

  const fetchTrips = async () => {
    try {
      // For loading: fetch planning/loading trips
      // For unloading: fetch in_transit/delivered trips
      const statuses = mode === 'loading' ? 'planning,loading' : 'in_transit,delivered';
      const response = await axios.get(`${API}/trips?status=${statuses}`, { withCredentials: true });
      setTrips(response.data);
    } catch (error) {
      console.error('Failed to fetch trips:', error);
      toast.error('Failed to load trips');
    }
  };

  // Refresh trips when mode changes
  useEffect(() => {
    fetchTrips();
    setSelectedTrip(null);
    clearSelections();
  }, [mode]);

  const fetchWarehouses = async () => {
    try {
      const response = await axios.get(`${API}/warehouses`, { withCredentials: true });
      setWarehouses(response.data);
    } catch (error) {
      console.error('Failed to fetch warehouses:', error);
    }
  };

  const fetchParcels = async () => {
    if (!selectedTrip) return;
    setLoading(true);
    
    try {
      if (mode === 'loading') {
        // LOADING MODE: Show staged vs loaded parcels
        // Fetch warehouse parcels (status: staged) - MUST have trip_id assigned
        const warehouseParams = {
          status: 'staged',
          trip_id: selectedTrip.id,
        };
        if (selectedWarehouse !== 'all') {
          warehouseParams.warehouse_id = selectedWarehouse;
        }
        
        const warehouseResponse = await axios.get(`${API}/shipments`, { 
          params: warehouseParams,
          withCredentials: true 
        });
        const filteredWarehouseParcels = warehouseResponse.data.filter(
          p => p.trip_id === selectedTrip.id
        );
        setWarehouseParcels(filteredWarehouseParcels);
        
        // Fetch truck parcels (status: loaded) - MUST have trip_id assigned
        const truckResponse = await axios.get(`${API}/shipments`, {
          params: {
            trip_id: selectedTrip.id,
            status: 'loaded',
          },
          withCredentials: true,
        });
        const filteredTruckParcels = truckResponse.data.filter(
          p => p.trip_id === selectedTrip.id
        );
        setTruckParcels(filteredTruckParcels);
      } else {
        // UNLOADING MODE: Show in_transit vs arrived parcels
        // Fetch in_transit parcels
        const inTransitResponse = await axios.get(`${API}/shipments`, {
          params: {
            trip_id: selectedTrip.id,
            status: 'in_transit',
          },
          withCredentials: true,
        });
        setInTransitParcels(inTransitResponse.data.filter(p => p.trip_id === selectedTrip.id));
        
        // Fetch arrived parcels
        const arrivedResponse = await axios.get(`${API}/shipments`, {
          params: {
            trip_id: selectedTrip.id,
            status: 'arrived',
          },
          withCredentials: true,
        });
        setArrivedParcels(arrivedResponse.data.filter(p => p.trip_id === selectedTrip.id));
      }
    } catch (error) {
      console.error('Failed to fetch parcels:', error);
      toast.error('Failed to load parcels');
    } finally {
      setLoading(false);
    }
  };

  const clearSelections = () => {
    setSelectedWarehouseParcels(new Set());
    setSelectedTruckParcels(new Set());
    setSelectedInTransitParcels(new Set());
    setSelectedArrivedParcels(new Set());
  };

  const handleBarcodeScan = async () => {
    if (!barcodeInput.trim() || !selectedTrip) return;
    
    setScanning(true);
    try {
      // Find the piece by barcode or parcel ID
      const scanResponse = await axios.get(`${API}/pieces/scan/${encodeURIComponent(barcodeInput.trim())}`, { withCredentials: true });
      const { piece, shipment } = scanResponse.data;
      
      if (shipment.trip_id !== selectedTrip.id) {
        toast.error('This parcel is not assigned to the selected trip');
        return;
      }
      
      // Determine new status based on mode
      // Loading mode: always load to truck (staged -> loaded)
      // Unloading mode: always mark as arrived (in_transit -> arrived)
      let newStatus;
      if (mode === 'loading') {
        newStatus = 'loaded';
      } else {
        newStatus = 'arrived';
      }
      
      const currentStatus = shipment.status;
      
      if (currentStatus === newStatus) {
        toast.warning(`Parcel is already ${newStatus}`);
        return;
      }
      
      // Check if parcel is invoiced before loading (in loading mode only)
      if (mode === 'loading' && !shipment.invoice_id) {
        toast.error('Cannot load parcel - not invoiced');
        return;
      }
      
      // Update shipment status
      await axios.put(`${API}/shipments/${shipment.id}`, {
        status: newStatus
      }, { withCredentials: true });
      
      // If loading to truck, mark piece as loaded
      if (mode === 'loading' && newStatus === 'loaded' && piece) {
        await axios.put(`${API}/pieces/${piece.id}/load`, {}, { withCredentials: true });
      }
      
      const actionText = mode === 'loading' ? 'loaded to truck' : 'marked as arrived';
      
      toast.success(`Parcel ${shipment.id.slice(0, 8).toUpperCase()} ${actionText}`);
      fetchParcels();
    } catch (error) {
      console.error('Scan error:', error);
      if (error.response?.status === 404) {
        toast.error('Parcel not found - check the barcode or ID');
      } else {
        toast.error(error.response?.data?.detail || 'Failed to process scan');
      }
    } finally {
      setScanning(false);
      setBarcodeInput('');
      barcodeRef.current?.focus();
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleBarcodeScan();
    }
  };

  // Manual move: staging -> truck (loading mode)
  const handleMoveToTruck = async () => {
    if (selectedWarehouseParcels.size === 0) return;
    
    // Check if all selected parcels are invoiced
    const selectedParcelsArray = warehouseParcels.filter(p => selectedWarehouseParcels.has(p.id));
    const nonInvoicedParcels = selectedParcelsArray.filter(p => !p.invoice_id && !p.invoice_number);
    
    if (nonInvoicedParcels.length > 0) {
      const parcelIds = nonInvoicedParcels.map(p => p.id.slice(0, 8).toUpperCase()).join(', ');
      toast.error(`Cannot load ${nonInvoicedParcels.length} parcel(s) - not invoiced: ${parcelIds}`);
      return;
    }
    
    setMoving(true);
    
    try {
      const parcelIds = Array.from(selectedWarehouseParcels);
      await axios.put(`${API}/warehouse/parcels/bulk-status`, {
        parcel_ids: parcelIds,
        status: 'loaded'
      }, { withCredentials: true });
      
      toast.success(`${parcelIds.length} parcel(s) loaded to truck`);
      setSelectedWarehouseParcels(new Set());
      fetchParcels();
    } catch (error) {
      toast.error('Failed to move parcels');
    } finally {
      setMoving(false);
    }
  };

  // Manual move: truck -> staging (loading mode)
  const handleReturnToWarehouse = async () => {
    if (selectedTruckParcels.size === 0) return;
    setMoving(true);
    
    try {
      const parcelIds = Array.from(selectedTruckParcels);
      await axios.put(`${API}/warehouse/parcels/bulk-status`, {
        parcel_ids: parcelIds,
        status: 'staged'
      }, { withCredentials: true });
      
      toast.success(`${parcelIds.length} parcel(s) returned to staging`);
      setSelectedTruckParcels(new Set());
      fetchParcels();
    } catch (error) {
      toast.error('Failed to move parcels');
    } finally {
      setMoving(false);
    }
  };

  // Manual move: in_transit -> arrived (unloading mode)
  const handleMarkArrived = async () => {
    if (selectedInTransitParcels.size === 0) return;
    setMoving(true);
    
    try {
      const parcelIds = Array.from(selectedInTransitParcels);
      await axios.put(`${API}/warehouse/parcels/bulk-status`, {
        parcel_ids: parcelIds,
        status: 'arrived'
      }, { withCredentials: true });
      
      toast.success(`${parcelIds.length} parcel(s) marked as arrived`);
      setSelectedInTransitParcels(new Set());
      fetchParcels();
    } catch (error) {
      toast.error('Failed to update parcels');
    } finally {
      setMoving(false);
    }
  };

  // Manual move: arrived -> in_transit (unloading mode)
  const handleReturnToTransit = async () => {
    if (selectedArrivedParcels.size === 0) return;
    setMoving(true);
    
    try {
      const parcelIds = Array.from(selectedArrivedParcels);
      await axios.put(`${API}/warehouse/parcels/bulk-status`, {
        parcel_ids: parcelIds,
        status: 'in_transit'
      }, { withCredentials: true });
      
      toast.success(`${parcelIds.length} parcel(s) returned to in-transit`);
      setSelectedArrivedParcels(new Set());
      fetchParcels();
    } catch (error) {
      toast.error('Failed to update parcels');
    } finally {
      setMoving(false);
    }
  };

  const handleMarkTruckLoaded = async () => {
    if (!selectedTrip) return;
    try {
      await axios.put(`${API}/trips/${selectedTrip.id}`, {
        status: 'in_transit'
      }, { withCredentials: true });
      toast.success('Trip marked as in transit');
      fetchTrips();
      setSelectedTrip(null);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update trip status');
    }
  };

  const handleOpenTruck = async () => {
    if (!selectedTrip) return;
    try {
      await axios.put(`${API}/trips/${selectedTrip.id}`, {
        status: 'loading'
      }, { withCredentials: true });
      toast.success('Trip reopened for loading');
      fetchTrips();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update trip status');
    }
  };

  const handleMarkDelivered = async () => {
    if (!selectedTrip) return;
    try {
      await axios.put(`${API}/trips/${selectedTrip.id}`, {
        status: 'delivered'
      }, { withCredentials: true });
      toast.success('Trip marked as delivered');
      fetchTrips();
      setSelectedTrip(null);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update trip status');
    }
  };

  // Toggle selection helpers
  const toggleSelection = (id, selectedSet, setSelectedSet) => {
    const newSet = new Set(selectedSet);
    if (newSet.has(id)) {
      newSet.delete(id);
    } else {
      newSet.add(id);
    }
    setSelectedSet(newSet);
  };

  const toggleSelectAll = (parcelsOrIds, selectedSet, setSelectedSet) => {
    // Support both array of parcels and array of IDs
    const ids = Array.isArray(parcelsOrIds) && parcelsOrIds.length > 0 && typeof parcelsOrIds[0] === 'string'
      ? parcelsOrIds
      : parcelsOrIds.map(p => p.id);
    
    if (selectedSet.size === ids.length && ids.length > 0) {
      setSelectedSet(new Set());
    } else {
      setSelectedSet(new Set(ids));
    }
  };

  // Calculate totals
  const warehouseCount = warehouseParcels.length;
  const truckCount = truckParcels.length;
  const totalCount = warehouseCount + truckCount;
  const warehouseWeight = warehouseParcels.reduce((sum, p) => sum + (p.total_weight || 0), 0);
  const truckWeight = truckParcels.reduce((sum, p) => sum + (p.total_weight || 0), 0);
  
  // Unloading mode totals
  const inTransitCount = inTransitParcels.length;
  const arrivedCount = arrivedParcels.length;
  const inTransitWeight = inTransitParcels.reduce((sum, p) => sum + (p.total_weight || 0), 0);
  const arrivedWeight = arrivedParcels.reduce((sum, p) => sum + (p.total_weight || 0), 0);

  // Parcel table component for reuse
  const ParcelTable = ({ parcels, selectedIds, onToggle, onToggleAll, colorClass, headerText, showInvoiceCheck = false }) => {
    // Filter out non-invoiced parcels from "select all" if showInvoiceCheck is true
    const selectableParcels = showInvoiceCheck 
      ? parcels.filter(p => p.invoice_id || p.invoice_number)
      : parcels;
    
    return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-[40px]">
            <Checkbox
              checked={selectedIds.size === selectableParcels.length && selectableParcels.length > 0}
              onCheckedChange={() => onToggleAll(selectableParcels.map(p => p.id))}
              data-testid={`select-all-${headerText.toLowerCase()}`}
            />
          </TableHead>
          <TableHead>Parcel #</TableHead>
          <TableHead>Client</TableHead>
          <TableHead>Description</TableHead>
          <TableHead className="text-right">Weight (kg)</TableHead>
          {showInvoiceCheck && <TableHead className="text-center">Invoice</TableHead>}
        </TableRow>
      </TableHeader>
      <TableBody>
        {loading ? (
          <TableRow>
            <TableCell colSpan={showInvoiceCheck ? 6 : 5} className="text-center py-8">
              <Loader2 className="h-6 w-6 animate-spin mx-auto" />
            </TableCell>
          </TableRow>
        ) : parcels.length === 0 ? (
          <TableRow>
            <TableCell colSpan={showInvoiceCheck ? 6 : 5} className="text-center py-8 text-muted-foreground">
              No parcels in {headerText.toLowerCase()}
            </TableCell>
          </TableRow>
        ) : parcels.map(parcel => {
          const isInvoiced = parcel.invoice_id || parcel.invoice_number;
          const isDisabled = showInvoiceCheck && !isInvoiced;
          
          return (
          <TableRow 
            key={parcel.id} 
            className={`hover:${colorClass}/50 ${selectedIds.has(parcel.id) ? colorClass + '/30' : ''} ${isDisabled ? 'opacity-60' : ''}`}
          >
            <TableCell>
              <Checkbox
                checked={selectedIds.has(parcel.id)}
                onCheckedChange={() => !isDisabled && onToggle(parcel.id)}
                disabled={isDisabled}
                data-testid={`select-${parcel.id}`}
                className={isDisabled ? 'cursor-not-allowed' : ''}
              />
            </TableCell>
            <TableCell>
              <div className="flex flex-col">
                <span className="font-mono text-sm">
                  {parcel.id.slice(0, 8).toUpperCase()}
                </span>
                {parcel.parcel_sequence && parcel.total_in_sequence && (
                  <span className="text-xs text-muted-foreground">
                    {parcel.parcel_sequence} of {parcel.total_in_sequence}
                  </span>
                )}
              </div>
            </TableCell>
            <TableCell className="font-medium">{parcel.client_name || '-'}</TableCell>
            <TableCell className="max-w-[200px] truncate">{parcel.description || '-'}</TableCell>
            <TableCell className="text-right font-mono">{parcel.total_weight?.toFixed(1) || '0'}</TableCell>
            {showInvoiceCheck && (
              <TableCell className="text-center">
                {isInvoiced ? (
                  <Badge variant="outline" className="text-xs text-green-600 border-green-300 bg-green-50">
                    {parcel.invoice_number || 'Invoiced'}
                  </Badge>
                ) : (
                  <Badge variant="outline" className="text-xs text-red-600 border-red-300 bg-red-50">
                    Not Invoiced
                  </Badge>
                )}
              </TableCell>
            )}
          </TableRow>
        )})}
      </TableBody>
    </Table>
  )};

  return (
    <Layout>
      <div className="space-y-6" data-testid="loading-page">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="font-heading text-2xl sm:text-3xl font-bold flex items-center gap-2">
              <Truck className="h-7 w-7 text-[#6B633C]" />
              Loading & Unloading
            </h1>
            <p className="text-muted-foreground mt-1">
              {mode === 'loading' 
                ? 'Scan or select parcels to load onto truck'
                : 'Scan or select parcels to mark as arrived at destination'
              }
            </p>
          </div>
          
          {/* Mode Toggle */}
          <Tabs value={mode} onValueChange={setMode} className="w-auto">
            <TabsList>
              <TabsTrigger value="loading" data-testid="loading-mode-btn">
                <Package className="h-4 w-4 mr-2" />
                Loading
              </TabsTrigger>
              <TabsTrigger value="unloading" data-testid="unloading-mode-btn">
                <Download className="h-4 w-4 mr-2" />
                Unloading
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </div>

        {/* Controls Row */}
        <Card>
          <CardContent className="p-4">
            <div className="flex flex-wrap items-end gap-4">
              {/* Trip Selection */}
              <div className="flex-1 min-w-[200px]">
                <Label className="text-sm font-medium mb-2 block">Select Trip</Label>
                <Select
                  value={selectedTrip?.id || ''}
                  onValueChange={(v) => {
                    setSelectedTrip(trips.find(t => t.id === v) || null);
                    clearSelections();
                  }}
                >
                  <SelectTrigger data-testid="trip-select">
                    <SelectValue placeholder={`Select a trip to ${mode}`} />
                  </SelectTrigger>
                  <SelectContent>
                    {trips.length === 0 ? (
                      <SelectItem value="none" disabled>No trips available</SelectItem>
                    ) : trips.map(trip => (
                      <SelectItem key={trip.id} value={trip.id}>
                        {trip.trip_number} - {trip.route?.join(' → ') || 'No route'} ({trip.status})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Warehouse Filter (only in loading mode) */}
              {mode === 'loading' && (
                <div className="min-w-[180px]">
                  <Label className="text-sm font-medium mb-2 block">Warehouse</Label>
                  <Select value={selectedWarehouse} onValueChange={setSelectedWarehouse}>
                    <SelectTrigger data-testid="warehouse-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Warehouses</SelectItem>
                      {warehouses.map(wh => (
                        <SelectItem key={wh.id} value={wh.id}>{wh.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}

              {/* Barcode Scanner */}
              <div className="flex-1 min-w-[250px]">
                <Label className="text-sm font-medium mb-2 block">Scan Parcel</Label>
                <div className="flex gap-2">
                  <Input
                    ref={barcodeRef}
                    value={barcodeInput}
                    onChange={(e) => setBarcodeInput(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="Scan barcode or enter parcel ID..."
                    disabled={!selectedTrip || scanning}
                    className="flex-1"
                    data-testid="barcode-input"
                  />
                  <Button 
                    onClick={handleBarcodeScan} 
                    disabled={!selectedTrip || !barcodeInput || scanning}
                    variant="secondary"
                  >
                    {scanning ? <Loader2 className="h-4 w-4 animate-spin" /> : <ScanLine className="h-4 w-4" />}
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  Scanned parcels will be {mode === 'loading' ? 'loaded to truck' : 'marked as arrived'}
                </p>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-2">
                {mode === 'loading' ? (
                  <>
                    <Button
                      onClick={handleMarkTruckLoaded}
                      disabled={!selectedTrip || truckCount === 0}
                      className="bg-green-600 hover:bg-green-700"
                      data-testid="mark-loaded-btn"
                    >
                      <Lock className="h-4 w-4 mr-2" />
                      Mark Truck Loaded
                    </Button>
                    <Button
                      onClick={handleOpenTruck}
                      disabled={!selectedTrip || selectedTrip?.status !== 'in_transit'}
                      variant="outline"
                      data-testid="open-truck-btn"
                    >
                      <Unlock className="h-4 w-4 mr-2" />
                      Open Truck
                    </Button>
                  </>
                ) : (
                  <Button
                    onClick={handleMarkDelivered}
                    disabled={!selectedTrip || inTransitCount > 0}
                    className="bg-green-600 hover:bg-green-700"
                    data-testid="mark-delivered-btn"
                  >
                    <Lock className="h-4 w-4 mr-2" />
                    Mark Trip Delivered
                  </Button>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Counters */}
        {selectedTrip && (
          <div className="grid grid-cols-3 gap-4">
            {mode === 'loading' ? (
              <>
                <Card className="bg-amber-50 border-amber-200">
                  <CardContent className="p-4 text-center">
                    <div className="text-3xl font-bold text-amber-700">{warehouseCount}</div>
                    <div className="text-sm text-amber-600">In Staging ({warehouseWeight.toFixed(1)} kg)</div>
                  </CardContent>
                </Card>
                <Card className="bg-green-50 border-green-200">
                  <CardContent className="p-4 text-center">
                    <div className="text-3xl font-bold text-green-700">{truckCount}</div>
                    <div className="text-sm text-green-600">On Truck ({truckWeight.toFixed(1)} kg)</div>
                  </CardContent>
                </Card>
                <Card className="bg-blue-50 border-blue-200">
                  <CardContent className="p-4 text-center">
                    <div className="text-3xl font-bold text-blue-700">{totalCount}</div>
                    <div className="text-sm text-blue-600">Total for Trip ({(warehouseWeight + truckWeight).toFixed(1)} kg)</div>
                  </CardContent>
                </Card>
              </>
            ) : (
              <>
                <Card className="bg-blue-50 border-blue-200">
                  <CardContent className="p-4 text-center">
                    <div className="text-3xl font-bold text-blue-700">{inTransitCount}</div>
                    <div className="text-sm text-blue-600">In Transit ({inTransitWeight.toFixed(1)} kg)</div>
                  </CardContent>
                </Card>
                <Card className="bg-green-50 border-green-200">
                  <CardContent className="p-4 text-center">
                    <div className="text-3xl font-bold text-green-700">{arrivedCount}</div>
                    <div className="text-sm text-green-600">Arrived ({arrivedWeight.toFixed(1)} kg)</div>
                  </CardContent>
                </Card>
                <Card className="bg-purple-50 border-purple-200">
                  <CardContent className="p-4 text-center">
                    <div className="text-3xl font-bold text-purple-700">{inTransitCount + arrivedCount}</div>
                    <div className="text-sm text-purple-600">Total ({(inTransitWeight + arrivedWeight).toFixed(1)} kg)</div>
                  </CardContent>
                </Card>
              </>
            )}
          </div>
        )}

        {/* Split Screen Tables */}
        {selectedTrip ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {mode === 'loading' ? (
              <>
                {/* Staging Table (Left) */}
                <Card>
                  <CardHeader className="bg-amber-50 border-b flex flex-row items-center justify-between py-3 px-4">
                    <CardTitle className="flex items-center gap-2 text-amber-800">
                      <WarehouseIcon className="h-5 w-5" />
                      Staging Area
                      <Badge variant="secondary" className="ml-2">{warehouseCount}</Badge>
                    </CardTitle>
                    <Button
                      size="sm"
                      onClick={handleMoveToTruck}
                      disabled={selectedWarehouseParcels.size === 0 || moving}
                      className="bg-amber-600 hover:bg-amber-700"
                    >
                      {moving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <ArrowRight className="h-4 w-4 mr-2" />}
                      Load Selected ({selectedWarehouseParcels.size})
                    </Button>
                  </CardHeader>
                  <CardContent className="p-0">
                    <div className="max-h-[500px] overflow-auto">
                      <ParcelTable
                        parcels={warehouseParcels}
                        selectedIds={selectedWarehouseParcels}
                        onToggle={(id) => toggleSelection(id, selectedWarehouseParcels, setSelectedWarehouseParcels)}
                        onToggleAll={(ids) => toggleSelectAll(ids || warehouseParcels, selectedWarehouseParcels, setSelectedWarehouseParcels)}
                        colorClass="bg-amber-50"
                        headerText="Staging"
                        showInvoiceCheck={true}
                      />
                    </div>
                  </CardContent>
                </Card>

                {/* Truck Table (Right) */}
                <Card>
                  <CardHeader className="bg-green-50 border-b flex flex-row items-center justify-between py-3 px-4">
                    <CardTitle className="flex items-center gap-2 text-green-800">
                      <Truck className="h-5 w-5" />
                      On Truck
                      <Badge variant="secondary" className="ml-2">{truckCount}</Badge>
                    </CardTitle>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={handleReturnToWarehouse}
                      disabled={selectedTruckParcels.size === 0 || moving}
                    >
                      {moving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <ArrowLeft className="h-4 w-4 mr-2" />}
                      Return Selected ({selectedTruckParcels.size})
                    </Button>
                  </CardHeader>
                  <CardContent className="p-0">
                    <div className="max-h-[500px] overflow-auto">
                      <ParcelTable
                        parcels={truckParcels}
                        selectedIds={selectedTruckParcels}
                        onToggle={(id) => toggleSelection(id, selectedTruckParcels, setSelectedTruckParcels)}
                        onToggleAll={(ids) => toggleSelectAll(ids || truckParcels, selectedTruckParcels, setSelectedTruckParcels)}
                        colorClass="bg-green-50"
                        headerText="Truck"
                      />
                    </div>
                  </CardContent>
                </Card>
              </>
            ) : (
              <>
                {/* In Transit Table (Left - Unloading Mode) */}
                <Card>
                  <CardHeader className="bg-blue-50 border-b flex flex-row items-center justify-between py-3 px-4">
                    <CardTitle className="flex items-center gap-2 text-blue-800">
                      <Truck className="h-5 w-5" />
                      In Transit
                      <Badge variant="secondary" className="ml-2">{inTransitCount}</Badge>
                    </CardTitle>
                    <Button
                      size="sm"
                      onClick={handleMarkArrived}
                      disabled={selectedInTransitParcels.size === 0 || moving}
                      className="bg-blue-600 hover:bg-blue-700"
                    >
                      {moving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <ArrowRight className="h-4 w-4 mr-2" />}
                      Mark Arrived ({selectedInTransitParcels.size})
                    </Button>
                  </CardHeader>
                  <CardContent className="p-0">
                    <div className="max-h-[500px] overflow-auto">
                      <ParcelTable
                        parcels={inTransitParcels}
                        selectedIds={selectedInTransitParcels}
                        onToggle={(id) => toggleSelection(id, selectedInTransitParcels, setSelectedInTransitParcels)}
                        onToggleAll={(ids) => toggleSelectAll(ids || inTransitParcels, selectedInTransitParcels, setSelectedInTransitParcels)}
                        colorClass="bg-blue-50"
                        headerText="In Transit"
                      />
                    </div>
                  </CardContent>
                </Card>

                {/* Arrived Table (Right - Unloading Mode) */}
                <Card>
                  <CardHeader className="bg-green-50 border-b flex flex-row items-center justify-between py-3 px-4">
                    <CardTitle className="flex items-center gap-2 text-green-800">
                      <Package className="h-5 w-5" />
                      Arrived
                      <Badge variant="secondary" className="ml-2">{arrivedCount}</Badge>
                    </CardTitle>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={handleReturnToTransit}
                      disabled={selectedArrivedParcels.size === 0 || moving}
                    >
                      {moving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <ArrowLeft className="h-4 w-4 mr-2" />}
                      Return to Transit ({selectedArrivedParcels.size})
                    </Button>
                  </CardHeader>
                  <CardContent className="p-0">
                    <div className="max-h-[500px] overflow-auto">
                      <ParcelTable
                        parcels={arrivedParcels}
                        selectedIds={selectedArrivedParcels}
                        onToggle={(id) => toggleSelection(id, selectedArrivedParcels, setSelectedArrivedParcels)}
                        onToggleAll={(ids) => toggleSelectAll(ids || arrivedParcels, selectedArrivedParcels, setSelectedArrivedParcels)}
                        colorClass="bg-green-50"
                        headerText="Arrived"
                      />
                    </div>
                  </CardContent>
                </Card>
              </>
            )}
          </div>
        ) : (
          <Card>
            <CardContent className="p-12 text-center">
              <Truck className="h-16 w-16 mx-auto mb-4 text-muted-foreground opacity-50" />
              <h3 className="text-lg font-medium mb-2">
                Select a Trip to Start {mode === 'loading' ? 'Loading' : 'Unloading'}
              </h3>
              <p className="text-muted-foreground">
                Choose a trip from the dropdown above to view and manage parcels
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </Layout>
  );
}

export default LoadingStaging;
