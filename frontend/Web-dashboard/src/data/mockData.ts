// ── Mock Data for MSME AI Platform ──

export const kpiData = [
  {
    id: 'revenue',
    title: 'Total Revenue',
    value: 2845900,
    prefix: '₹',
    formatted: '₹28,45,900',
    change: '+12.4%',
    changeLabel: 'this month',
    changeType: 'success' as const,
    sparkline: [20, 35, 28, 45, 38, 52, 48, 62],
    color: '#F96A2A',
  },
  {
    id: 'invoices',
    title: 'Active Invoices',
    value: 142,
    prefix: '',
    formatted: '142',
    change: '14 overdue',
    changeLabel: '',
    changeType: 'warning' as const,
    sparkline: [30, 42, 35, 50, 45, 55, 48, 60],
    color: '#FF8C42',
  },
  {
    id: 'lowstock',
    title: 'Low Stock SKUs',
    value: 7,
    prefix: '',
    formatted: '7',
    change: 'Reorder needed',
    changeLabel: '',
    changeType: 'error' as const,
    sparkline: [10, 8, 12, 6, 9, 7, 11, 7],
    color: '#888888',
  },
  {
    id: 'hitl',
    title: 'HITL Pending',
    value: 3,
    prefix: '',
    formatted: '3',
    change: 'Awaiting approval',
    changeLabel: '',
    changeType: 'warning' as const,
    sparkline: [2, 5, 3, 4, 2, 6, 3, 3],
    color: '#F96A2A',
  },
];

export const revenueData = [
  { month: 'Jan', value: 1.8 },
  { month: 'Feb', value: 2.1 },
  { month: 'Mar', value: 3.2 },
  { month: 'Apr', value: 2.5 },
  { month: 'May', value: 2.9 },
  { month: 'Jun', value: 3.8 },
  { month: 'Jul', value: 3.1 },
  { month: 'Aug', value: 2.7 },
  { month: 'Sep', value: 3.5 },
  { month: 'Oct', value: 4.0 },
  { month: 'Nov', value: 3.6 },
  { month: 'Dec', value: 2.8 },
];

export const revenueSources = [
  { name: 'Organic Search', value: 62, color: '#F96A2A' },
  { name: 'Direct', value: 48, color: '#FF8C42' },
  { name: 'Social', value: 35, color: '#888888' },
  { name: 'Email', value: 28, color: '#CCCCCC' },
  { name: 'Referral', value: 19, color: '#666666' },
];

export interface ActivityItem {
  id: string;
  agent: string;
  agentColor: string;
  icon: string;
  description: string;
  timestamp: string;
  status: 'COMPLETED' | 'PENDING HITL' | 'FAILED';
}

export const activityLog: ActivityItem[] = [
  {
    id: '1',
    agent: 'Billing',
    agentColor: '#F96A2A',
    icon: 'Receipt',
    description: 'Generated GST invoice INV-2024-0148 for Rajan Stores',
    timestamp: '2 min ago',
    status: 'COMPLETED',
  },
  {
    id: '2',
    agent: 'Inventory',
    agentColor: '#FF8C42',
    icon: 'Package',
    description: 'Stockout prediction: SKU-4421 below threshold in 3 days',
    timestamp: '5 min ago',
    status: 'PENDING HITL',
  },
  {
    id: '3',
    agent: 'Accounting',
    agentColor: '#888888',
    icon: 'BarChart3',
    description: 'Reconciled ₹4,28,500 across 23 transactions',
    timestamp: '8 min ago',
    status: 'COMPLETED',
  },
  {
    id: '4',
    agent: 'CRM',
    agentColor: '#F96A2A',
    icon: 'MessageSquare',
    description: 'Follow-up email sent to 8 overdue accounts',
    timestamp: '12 min ago',
    status: 'COMPLETED',
  },
  {
    id: '5',
    agent: 'Credit',
    agentColor: '#FF8C42',
    icon: 'CreditCard',
    description: 'Credit score analysis failed for vendor V-0932',
    timestamp: '15 min ago',
    status: 'FAILED',
  },
  {
    id: '6',
    agent: 'HR',
    agentColor: '#CCCCCC',
    icon: 'Users',
    description: 'Payroll computed for 12 employees — ₹3,84,000',
    timestamp: '18 min ago',
    status: 'COMPLETED',
  },
  {
    id: '7',
    agent: 'Billing',
    agentColor: '#F96A2A',
    icon: 'Receipt',
    description: 'Bulk invoice batch for 15 customers awaiting approval',
    timestamp: '22 min ago',
    status: 'PENDING HITL',
  },
  {
    id: '8',
    agent: 'Inventory',
    agentColor: '#FF8C42',
    icon: 'Package',
    description: 'Auto-generated PO for 5 SKUs from preferred vendor',
    timestamp: '28 min ago',
    status: 'COMPLETED',
  },
];

export const additionalActivities: ActivityItem[] = [
  {
    id: 'extra-1',
    agent: 'CRM',
    agentColor: '#F96A2A',
    icon: 'MessageSquare',
    description: 'New lead captured: Shree Industries (Pune)',
    timestamp: 'Just now',
    status: 'COMPLETED',
  },
  {
    id: 'extra-2',
    agent: 'Accounting',
    agentColor: '#888888',
    icon: 'BarChart3',
    description: 'GSTR-1 filing draft ready for review',
    timestamp: 'Just now',
    status: 'PENDING HITL',
  },
  {
    id: 'extra-3',
    agent: 'Credit',
    agentColor: '#FF8C42',
    icon: 'CreditCard',
    description: 'Vendor payment ₹1,25,000 scheduled for approval',
    timestamp: 'Just now',
    status: 'PENDING HITL',
  },
];

export interface HITLItem {
  id: string;
  agent: string;
  agentColor: string;
  risk: 'HIGH' | 'MEDIUM' | 'LOW';
  title: string;
  preview: string;
  timestamp: string;
  geometry: string;
}

export const hitlItems: HITLItem[] = [
  {
    id: 'hitl-1',
    agent: 'BILLING',
    agentColor: '#F96A2A',
    risk: 'HIGH',
    title: 'Send GST Invoice to 15 customers — ₹2,84,590 total',
    preview: `INV-2024-0148  |  Rajan Stores
HSN: 6403  |  GST: 18%
Amount: ₹18,940 × 15 customers
Total: ₹2,84,590
IRN: Auto-generated
E-way bill: Required`,
    timestamp: '3 min ago',
    geometry: 'octahedron',
  },
  {
    id: 'hitl-2',
    agent: 'INVENTORY',
    agentColor: '#FF8C42',
    risk: 'MEDIUM',
    title: 'Auto-reorder 5 SKUs from preferred vendor',
    preview: `Purchase Order PO-2024-0089
Vendor: ABC Suppliers (Mumbai)
SKU-4421: Qty 200 @ ₹45/unit
SKU-4455: Qty 150 @ ₹82/unit
SKU-4490: Qty 300 @ ₹23/unit
Total: ₹42,350`,
    timestamp: '8 min ago',
    geometry: 'tetrahedron',
  },
  {
    id: 'hitl-3',
    agent: 'ACCOUNTING',
    agentColor: '#888888',
    risk: 'HIGH',
    title: 'File GSTR-1 for March 2024 — 142 invoices',
    preview: `GSTR-1 Monthly Return
Period: March 2024
B2B Invoices: 89
B2C Invoices: 53
Total Taxable: ₹28,45,900
CGST: ₹2,56,131
SGST: ₹2,56,131`,
    timestamp: '15 min ago',
    geometry: 'box',
  },
];

export const inventoryData = [
  { sku: 'SKU-4401', name: 'Cotton Thread Roll (500m)', category: 'Raw Material', qty: 450, reorder: 100, status: 'adequate' as const, forecast: [450, 430, 410, 390, 370, 350, 330], price: 125 },
  { sku: 'SKU-4412', name: 'Polyester Fabric (1m²)', category: 'Raw Material', qty: 85, reorder: 100, status: 'low' as const, forecast: [120, 110, 100, 90, 85, 75, 60], price: 340 },
  { sku: 'SKU-4421', name: 'Metal Buttons (100pc)', category: 'Accessories', qty: 25, reorder: 50, status: 'critical' as const, forecast: [80, 65, 50, 40, 30, 25, 15], price: 45 },
  { sku: 'SKU-4435', name: 'Zipper Roll (50m)', category: 'Accessories', qty: 200, reorder: 75, status: 'adequate' as const, forecast: [200, 195, 185, 180, 175, 170, 160], price: 89 },
  { sku: 'SKU-4442', name: 'Packaging Boxes (50pc)', category: 'Packaging', qty: 42, reorder: 50, status: 'low' as const, forecast: [90, 75, 65, 55, 45, 42, 35], price: 210 },
  { sku: 'SKU-4455', name: 'Elastic Band (100m)', category: 'Accessories', qty: 15, reorder: 30, status: 'critical' as const, forecast: [50, 40, 30, 25, 20, 15, 8], price: 82 },
  { sku: 'SKU-4468', name: 'Dye Powder (1kg)', category: 'Chemical', qty: 320, reorder: 100, status: 'adequate' as const, forecast: [320, 310, 300, 295, 290, 280, 270], price: 560 },
  { sku: 'SKU-4490', name: 'Sewing Needles (200pc)', category: 'Tools', qty: 18, reorder: 40, status: 'critical' as const, forecast: [65, 55, 45, 35, 25, 18, 10], price: 23 },
];

export const reasoningSteps = [
  { type: 'REASON' as const, content: 'Invoice detected for Rajan Stores. HSN validation needed.', icon: 'Brain' },
  { type: 'ACT' as const, content: "Called validate_hsn(code='6403')", icon: 'Zap' },
  { type: 'OBSERVE' as const, content: 'HSN valid. GST rate: 18%', icon: 'Eye' },
  { type: 'ACT' as const, content: "Called generate_pdf(invoice_id='INV-0148')", icon: 'Zap' },
  { type: 'OBSERVE' as const, content: 'PDF generated at /tmp/INV-0148.pdf', icon: 'Eye' },
  { type: 'HITL' as const, content: 'Approval required: send to 15 customers', icon: 'Bell' },
];

export const howItWorksSteps = [
  { name: 'TRIGGER', description: 'Event detected from Tally sync or schedule' },
  { name: 'INGEST', description: 'Raw data parsed and normalized' },
  { name: 'ORCHESTRATE', description: 'LangGraph routes to correct agent' },
  { name: 'EXECUTE', description: 'Agent runs ReAct reasoning loop' },
  { name: 'TOOL CALL', description: 'External APIs and databases queried' },
  { name: 'HITL CHECK', description: 'Risk assessment determines approval need' },
  { name: 'APPROVE', description: 'Human reviews and approves/rejects' },
  { name: 'SYNC & LOG', description: 'Results synced back and audit logged' },
];

export const tickerItems = [
  '₹12Cr+ invoices processed',
  '6 autonomous agents',
  'AES-256 encryption',
  'Offline-first',
  '500+ MSMEs',
  'Tally-transparent',
  'India-built',
  'LangGraph powered',
  'Privacy-first',
  'ReAct loop',
];

export const sidebarNavItems = [
  { label: 'Dashboard', icon: 'LayoutDashboard', path: '/dashboard' },
  { label: 'Billing', icon: 'Receipt', path: '/dashboard' },
  { label: 'Inventory', icon: 'Package', path: '/inventory' },
  { label: 'Accounting', icon: 'BarChart3', path: '/dashboard' },
  { label: 'HR & Payroll', icon: 'Users', path: '/dashboard' },
  { label: 'CRM', icon: 'MessageSquare', path: '/dashboard' },
  { label: 'Credit', icon: 'CreditCard', path: '/dashboard' },
];

export const sidebarSystemItems = [
  { label: 'HITL Inbox', icon: 'BellRing', path: '/hitl', badge: 3 },
  { label: 'Settings', icon: 'Settings', path: '/dashboard' },
];
