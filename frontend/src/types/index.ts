export interface User {
  id: number;
  email: string;
  full_name?: string;
  phone?: string;
  vehicle_number?: string;
  is_active: boolean;
  is_superuser?: boolean;
  role?: string;
  created_at: string;
}

export interface Token {
  access_token: string;
  token_type: string;
}

export type ParkingSlotStatus = "available" | "occupied" | "reserved" | "maintenance";

export type VehicleType = "car" | "motorcycle" | "bicycle" | "truck" | "other";

export interface Facility {
  id: number;
  name: string;
  description?: string;
  address: string;
  city?: string;
  state?: string;
  postal_code?: string;
  latitude?: number;
  longitude?: number;
  total_slots: number;
  operating_start_time?: string;
  operating_end_time?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Zone {
  id: number;
  facility_id: number;
  name: string;
  description?: string;
  floor_number?: number;
  total_slots: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Slot {
  id: number;
  zone_id: number;
  slot_number: string;
  status: ParkingSlotStatus;
  vehicle_type: VehicleType;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Availability {
  entity_id: number;
  total_slots: number;
  available: number;
  occupied: number;
  reserved: number;
  occupancy_percentage: number;
}

export type ReservationStatus = "pending" | "confirmed" | "cancelled" | "completed";

export interface Reservation {
  id: number;
  user_id: number;
  slot_id: number;
  reservation_start: string;
  reservation_end: string;
  status: ReservationStatus;
}

export type ParkingSessionStatus = "active" | "completed";

export interface ParkingSession {
  id: number;
  user_id: number;
  slot_id: number;
  reservation_id?: number;
  check_in_time: string;
  check_out_time?: string;
  duration_minutes?: number;
  fee_amount?: number;
  status: ParkingSessionStatus;
  created_at: string;
  updated_at: string;
}

export type PaymentMethod = "credit_card" | "debit_card" | "wallet" | "cash";

export type PaymentStatus = "pending" | "completed" | "failed" | "refunded";

export interface Payment {
  id: number;
  session_id: number;
  user_id: number;
  amount: number;
  payment_method: PaymentMethod;
  payment_status: PaymentStatus;
  transaction_id?: string;
  paid_at?: string;
  created_at: string;
  updated_at: string;
}

export interface APIError {
  detail: string;
}

export interface WebSocketMessage {
  type: string;
  data: any;
}
