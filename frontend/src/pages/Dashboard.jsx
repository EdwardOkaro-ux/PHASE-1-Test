import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { Layout } from '../components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Skeleton } from '../components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import { Package, Users, Truck, Warehouse, ArrowRight, TrendingUp, PackagePlus } from 'lucide-react';
import { cn } from '../lib/utils';

const API = `${window.location.origin}/api`;

const statusColors = {
  warehouse: 'status-warehouse',
  staged: 'status-staged',
  loaded: 'status-loaded',
  in_transit: 'status-in-transit',
  delivered: 'status-delivered'
};

export function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API}/dashboard/stats`, {
        withCredentials: true
      });
      setStats(response.data);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const statCards = [
    {
      title: 'Total Clients',
      value: stats?.total_clients || 0,
      icon: Users,
      href: '/clients',
      color: 'text-blue-500'
    },
    {
      title: 'Total Shipments',
      value: stats?.total_shipments || 0,
      icon: Package,
      href: '/shipments',
      color: 'text-primary'
    },
    {
      title: 'Active Trips',
      value: stats?.total_trips || 0,
      icon: Truck,
      href: '/trips',
      color: 'text-accent'
    },
    {
      title: 'In Warehouse',
      value: stats?.shipment_status?.warehouse || 0,
      icon: Warehouse,
      href: '/shipments?status=warehouse',
      color: 'text-purple-500'
    }
  ];

  return (
    <Layout>
      <div className="space-y-6" data-testid="dashboard-page">
        {/* Welcome Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="font-heading text-2xl sm:text-3xl font-bold">Dashboard</h1>
            <p className="text-muted-foreground mt-1">Overview of your logistics operations</p>
          </div>
          <div className="flex gap-2">
            <Button asChild variant="outline">
              <Link to="/scanner" data-testid="quick-scan-btn">
                Quick Scan
              </Link>
            </Button>
            <Button asChild className="bg-[#6B633C] hover:bg-[#6B633C]/90">
              <Link to="/parcels/intake" data-testid="add-parcel-btn">
                <PackagePlus className="h-4 w-4 mr-2" />
                Add Parcel
              </Link>
            </Button>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {statCards.map((stat, i) => (
            <Card key={i} className="hover:shadow-md transition-shadow">
              <CardContent className="p-4 sm:p-6">
                {loading ? (
                  <div className="space-y-3">
                    <Skeleton className="h-4 w-24" />
                    <Skeleton className="h-8 w-16" />
                  </div>
                ) : (
                  <Link to={stat.href} className="block" data-testid={`stat-card-${i}`}>
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="text-sm text-muted-foreground">{stat.title}</p>
                        <p className="text-2xl sm:text-3xl font-bold font-mono mt-1">
                          {stat.value.toLocaleString()}
                        </p>
                      </div>
                      <div className={cn('h-10 w-10 rounded-lg bg-muted flex items-center justify-center', stat.color)}>
                        <stat.icon className="h-5 w-5" />
                      </div>
                    </div>
                  </Link>
                )}
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Status Breakdown */}
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Shipment Status */}
          <Card className="lg:col-span-1">
            <CardHeader className="pb-2">
              <CardTitle className="text-lg font-heading">Shipment Status</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="space-y-3">
                  {[1, 2, 3].map((i) => (
                    <Skeleton key={i} className="h-10 w-full" />
                  ))}
                </div>
              ) : (
                <div className="space-y-3">
                  {[
                    { label: 'In Warehouse', value: stats?.shipment_status?.warehouse || 0, status: 'warehouse' },
                    { label: 'In Transit', value: stats?.shipment_status?.in_transit || 0, status: 'in_transit' },
                    { label: 'Delivered', value: stats?.shipment_status?.delivered || 0, status: 'delivered' }
                  ].map((item, i) => (
                    <div
                      key={i}
                      className="flex items-center justify-between p-3 rounded-lg bg-muted/50"
                      data-testid={`status-${item.status}`}
                    >
                      <div className="flex items-center gap-3">
                        <Badge className={cn('text-xs', statusColors[item.status])}>
                          {item.status.replace('_', ' ')}
                        </Badge>
                        <span className="text-sm font-medium">{item.label}</span>
                      </div>
                      <span className="font-mono font-semibold">{item.value}</span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Recent Shipments */}
          <Card className="lg:col-span-2">
            <CardHeader className="pb-2 flex flex-row items-center justify-between">
              <CardTitle className="text-lg font-heading">Recent Shipments</CardTitle>
              <Button variant="ghost" size="sm" asChild>
                <Link to="/shipments" data-testid="view-all-shipments">
                  View All
                  <ArrowRight className="ml-1 h-4 w-4" />
                </Link>
              </Button>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="space-y-3">
                  {[1, 2, 3, 4, 5].map((i) => (
                    <Skeleton key={i} className="h-12 w-full" />
                  ))}
                </div>
              ) : stats?.recent_shipments?.length > 0 ? (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Client</TableHead>
                        <TableHead className="hidden sm:table-cell">Destination</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead className="text-right">Weight</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {stats.recent_shipments.map((shipment) => (
                        <TableRow key={shipment.id} data-testid={`shipment-row-${shipment.id}`}>
                          <TableCell className="font-medium">
                            {shipment.client_name}
                          </TableCell>
                          <TableCell className="hidden sm:table-cell text-muted-foreground">
                            {shipment.destination}
                          </TableCell>
                          <TableCell>
                            <Badge className={cn('text-xs capitalize', statusColors[shipment.status])}>
                              {shipment.status.replace('_', ' ')}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-right font-mono">
                            {shipment.total_weight} kg
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <Package className="h-12 w-12 mx-auto mb-3 opacity-50" />
                  <p>No shipments yet</p>
                  <Button asChild variant="link" className="mt-2">
                    <Link to="/shipments/new">Create your first shipment</Link>
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Quick Actions */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-lg font-heading">Quick Actions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <Button variant="outline" asChild className="h-auto py-4 flex-col">
                <Link to="/clients/new" data-testid="quick-add-client">
                  <Users className="h-5 w-5 mb-2" />
                  Add Client
                </Link>
              </Button>
              <Button variant="outline" asChild className="h-auto py-4 flex-col">
                <Link to="/shipments/new" data-testid="quick-add-shipment">
                  <Package className="h-5 w-5 mb-2" />
                  New Shipment
                </Link>
              </Button>
              <Button variant="outline" asChild className="h-auto py-4 flex-col">
                <Link to="/trips/new" data-testid="quick-add-trip">
                  <Truck className="h-5 w-5 mb-2" />
                  Create Trip
                </Link>
              </Button>
              <Button variant="outline" asChild className="h-auto py-4 flex-col">
                <Link to="/scanner" data-testid="quick-scanner">
                  <TrendingUp className="h-5 w-5 mb-2" />
                  Scan Barcode
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}
