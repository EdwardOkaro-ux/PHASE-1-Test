import { useState, useEffect } from 'react';
import axios from 'axios';
import { Layout } from '../components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Skeleton } from '../components/ui/skeleton';
import { Avatar, AvatarFallback, AvatarImage } from '../components/ui/avatar';
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
import { Plus, MoreVertical, Edit, Trash2, UserCircle, Shield, Mail, Warehouse } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { cn } from '../lib/utils';

const API = `${window.location.origin}/api`;

const roleColors = {
  owner: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400',
  manager: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  warehouse: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
  finance: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
  driver: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400'
};

const statusColors = {
  active: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
  invited: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  suspended: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
};

export function Team() {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState([]);
  const [warehouses, setWarehouses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    role: 'warehouse',
    phone: '',
    default_warehouse: ''
  });

  useEffect(() => {
    fetchUsers();
    fetchWarehouses();
  }, []);

  const fetchUsers = async () => {
    try {
      const response = await axios.get(`${API}/users`, { withCredentials: true });
      setUsers(response.data);
    } catch (error) {
      toast.error('Failed to fetch team members');
    } finally {
      setLoading(false);
    }
  };

  const fetchWarehouses = async () => {
    try {
      const response = await axios.get(`${API}/warehouses`, { withCredentials: true });
      setWarehouses(response.data);
    } catch (error) {
      console.error('Failed to fetch warehouses');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingUser) {
        await axios.put(`${API}/users/${editingUser.id}`, {
          name: formData.name,
          role: formData.role,
          phone: formData.phone,
          default_warehouse: formData.default_warehouse || null
        }, { withCredentials: true });
        toast.success('User updated');
      } else {
        await axios.post(`${API}/users`, {
          ...formData,
          default_warehouse: formData.default_warehouse || null
        }, { withCredentials: true });
        toast.success('User invited');
      }
      setDialogOpen(false);
      resetForm();
      fetchUsers();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save user');
    }
  };

  const handleDelete = async (userId) => {
    if (!window.confirm('Are you sure you want to remove this team member?')) return;
    try {
      await axios.delete(`${API}/users/${userId}`, { withCredentials: true });
      toast.success('User removed');
      fetchUsers();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to remove user');
    }
  };

  const handleUpdateStatus = async (userId, newStatus) => {
    try {
      await axios.put(`${API}/users/${userId}`, { status: newStatus }, { withCredentials: true });
      toast.success('Status updated');
      fetchUsers();
    } catch (error) {
      toast.error('Failed to update status');
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      email: '',
      role: 'warehouse',
      phone: '',
      default_warehouse: ''
    });
    setEditingUser(null);
  };

  const openEdit = (user) => {
    setEditingUser(user);
    setFormData({
      name: user.name,
      email: user.email,
      role: user.role,
      phone: user.phone || '',
      default_warehouse: user.default_warehouse || ''
    });
    setDialogOpen(true);
  };

  const getWarehouseName = (warehouseId) => {
    if (!warehouseId) return '-';
    const wh = warehouses.find(w => w.id === warehouseId);
    return wh?.name || 'Unknown';
  };

  const isOwner = currentUser?.role === 'owner';

  return (
    <Layout>
      <div className="space-y-6" data-testid="team-page">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="font-heading text-2xl sm:text-3xl font-bold">Team</h1>
            <p className="text-muted-foreground mt-1">Manage your team members and roles</p>
          </div>
          
          <Dialog open={dialogOpen} onOpenChange={(open) => { setDialogOpen(open); if (!open) resetForm(); }}>
            <DialogTrigger asChild>
              <Button data-testid="add-user-btn">
                <Plus className="h-4 w-4 mr-2" />
                Add User
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-md">
              <DialogHeader>
                <DialogTitle>{editingUser ? 'Edit User' : 'Add Team Member'}</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Full Name *</Label>
                  <Input
                    id="name"
                    placeholder="John Doe"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    required
                    data-testid="user-name-input"
                  />
                </div>
                
                {!editingUser && (
                  <div className="space-y-2">
                    <Label htmlFor="email">Email Address *</Label>
                    <Input
                      id="email"
                      type="email"
                      placeholder="john@example.com"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      required
                      data-testid="user-email-input"
                    />
                  </div>
                )}
                
                <div className="space-y-2">
                  <Label htmlFor="phone">Phone Number</Label>
                  <Input
                    id="phone"
                    placeholder="+27..."
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    data-testid="user-phone-input"
                  />
                </div>
                
                <div className="space-y-2">
                  <Label>Role *</Label>
                  <Select
                    value={formData.role}
                    onValueChange={(value) => setFormData({ ...formData, role: value })}
                  >
                    <SelectTrigger data-testid="user-role-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="owner">Owner</SelectItem>
                      <SelectItem value="manager">Manager</SelectItem>
                      <SelectItem value="warehouse">Warehouse</SelectItem>
                      <SelectItem value="finance">Finance</SelectItem>
                      <SelectItem value="driver">Driver</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Default Warehouse</Label>
                  <Select
                    value={formData.default_warehouse || 'none'}
                    onValueChange={(value) => setFormData({ ...formData, default_warehouse: value === 'none' ? '' : value })}
                  >
                    <SelectTrigger data-testid="user-warehouse-select">
                      <Warehouse className="h-4 w-4 mr-2" />
                      <SelectValue placeholder="Select default warehouse" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">No default</SelectItem>
                      {warehouses.map(wh => (
                        <SelectItem key={wh.id} value={wh.id}>{wh.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">
                    This warehouse will be pre-selected when the user opens the Warehouse page
                  </p>
                </div>
                
                <DialogFooter>
                  <Button type="submit" data-testid="save-user-btn">
                    {editingUser ? 'Update' : 'Invite'} User
                  </Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        {/* Users Table */}
        <Card>
          <CardContent className="p-0">
            {loading ? (
              <div className="p-6 space-y-3">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-16 w-full" />
                ))}
              </div>
            ) : users.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="pl-6">User</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead className="hidden md:table-cell">Default Warehouse</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right pr-6">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {users.map((user) => (
                    <TableRow key={user.id} data-testid={`user-row-${user.id}`}>
                      <TableCell className="pl-6">
                        <div className="flex items-center gap-3">
                          <Avatar className="h-10 w-10">
                            <AvatarImage src={user.picture} />
                            <AvatarFallback className="bg-primary/10 text-primary">
                              {user.name?.charAt(0)?.toUpperCase() || 'U'}
                            </AvatarFallback>
                          </Avatar>
                          <div>
                            <p className="font-medium">{user.name}</p>
                            <p className="text-sm text-muted-foreground">{user.email}</p>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge className={cn('border-0', roleColors[user.role])}>
                          {user.role?.charAt(0).toUpperCase() + user.role?.slice(1)}
                        </Badge>
                      </TableCell>
                      <TableCell className="hidden md:table-cell">
                        <span className="text-sm text-muted-foreground">
                          {getWarehouseName(user.default_warehouse)}
                        </span>
                      </TableCell>
                      <TableCell>
                        <Badge className={cn('border-0', statusColors[user.status])}>
                          {user.status?.charAt(0).toUpperCase() + user.status?.slice(1)}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right pr-6">
                        {isOwner && user.id !== currentUser?.id && (
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="icon" data-testid={`user-menu-${user.id}`}>
                                <MoreVertical className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem onClick={() => openEdit(user)}>
                                <Edit className="h-4 w-4 mr-2" />
                                Edit
                              </DropdownMenuItem>
                              {user.status === 'active' ? (
                                <DropdownMenuItem onClick={() => handleUpdateStatus(user.id, 'suspended')}>
                                  <Shield className="h-4 w-4 mr-2" />
                                  Suspend
                                </DropdownMenuItem>
                              ) : user.status === 'suspended' ? (
                                <DropdownMenuItem onClick={() => handleUpdateStatus(user.id, 'active')}>
                                  <Shield className="h-4 w-4 mr-2" />
                                  Activate
                                </DropdownMenuItem>
                              ) : null}
                              <DropdownMenuItem
                                onClick={() => handleDelete(user.id)}
                                className="text-destructive"
                              >
                                <Trash2 className="h-4 w-4 mr-2" />
                                Remove
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="text-center py-12 text-muted-foreground">
                <UserCircle className="h-12 w-12 mx-auto mb-3 opacity-50" />
                <p>No team members yet</p>
                <Button
                  variant="link"
                  onClick={() => setDialogOpen(true)}
                  className="mt-2"
                >
                  Add your first team member
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}
