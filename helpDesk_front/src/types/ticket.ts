export const TicketStatus = {
  DRAFT: 'draft',
  PENDING_APPROVAL: 'pending_approval',
  REJECTED: 'rejected',
  APPROVED: 'approved',
  ASSIGNED: 'assigned',
  IN_PROGRESS: 'in_progress',
  WAITING_INFO: 'waiting_info',
  COMPLETED: 'completed',
  CLOSED: 'closed',
} as const;

export type TicketStatus = (typeof TicketStatus)[keyof typeof TicketStatus];

export const TicketPriority = {
  LOW: 'low',
  NORMAL: 'normal',
  HIGH: 'high',
  URGENT: 'urgent',
} as const;

export type TicketPriority = (typeof TicketPriority)[keyof typeof TicketPriority];

export const TicketSlaStatus = {
  ON_TRACK: 'on_track',
  AT_RISK: 'at_risk',
  OVERDUE: 'overdue',
  COMPLETED_ON_TIME: 'completed_on_time',
  COMPLETED_LATE: 'completed_late',
} as const;

export type TicketSlaStatus = (typeof TicketSlaStatus)[keyof typeof TicketSlaStatus];

export interface TicketUserInfo {
  id: string;
  full_name: string;
  email: string;
}

export interface TicketDepartmentInfo {
  id: string;
  name: string;
  code: string;
}

export interface TicketSlaInfo {
  status: TicketSlaStatus;
  planned_completion_date: string | null;
}

export interface Ticket {
  id: string;
  ticket_number: string;
  title: string;
  description: string;
  status: TicketStatus;
  priority: TicketPriority;
  category_id: string;
  template_id: string | null;
  created_by_id: string;
  creator_department_id: string;
  assigned_department_id: string | null;
  assigned_by_user_id: string | null;
  approver_user_id: string | null;
  completed_by_id: string | null;
  closed_by_id: string | null;
  desired_completion_date: string | null;
  planned_completion_date: string | null;
  actual_completion_date: string | null;
  approved_at: string | null;
  assigned_at: string | null;
  completed_at: string | null;
  closed_at: string | null;
  approver_comment: string | null;
  completion_comment: string | null;
  closed_comment: string | null;
  is_urgent: boolean;
  progress_percent: number;
  created_at: string;
  updated_at: string;
  ticket_metadata: Record<string, unknown> | null;
  // Optional related objects
  created_by?: TicketUserInfo | null;
  creator_department?: TicketDepartmentInfo | null;
  assigned_department?: TicketDepartmentInfo | null;
  approver?: TicketUserInfo | null;
  assigned_by?: TicketUserInfo | null;
  completed_by?: TicketUserInfo | null;
  closed_by?: TicketUserInfo | null;
  executors?: TicketUserInfo[];
  sla: TicketSlaInfo | null;
}

export interface TicketListResponse {
  items: Ticket[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface TicketComment {
  id: string;
  ticket_id: string;
  author_id: string;
  author_full_name: string;
  body: string;
  created_at: string;
}

export interface TicketCommentListResponse {
  items: TicketComment[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

// Helper type for Kanban column mapping
export type KanbanColumnStatus = 
  | 'new' 
  | 'assigned' 
  | 'in_progress' 
  | 'completed' 
  | 'closed';

export const STATUS_TO_COLUMN_MAP: Record<TicketStatus, KanbanColumnStatus> = {
  [TicketStatus.DRAFT]: 'new',
  [TicketStatus.PENDING_APPROVAL]: 'new',
  [TicketStatus.REJECTED]: 'new', // Can be filtered separately
  [TicketStatus.APPROVED]: 'assigned',
  [TicketStatus.ASSIGNED]: 'assigned',
  [TicketStatus.IN_PROGRESS]: 'in_progress',
  [TicketStatus.WAITING_INFO]: 'in_progress',
  [TicketStatus.COMPLETED]: 'completed',
  [TicketStatus.CLOSED]: 'closed',
};
