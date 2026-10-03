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

export interface UserLoginRequest {
  email: string;
  password: string;
}

export interface UserRegisterRequest {
  email: string;
  password: string;
  full_name?: string;
  phone?: string;
  vehicle_number?: string;
}

export interface UserUpdateRequest {
  full_name?: string;
  phone?: string;
  vehicle_number?: string;
}

export type ParkingSlotStatus = "available" | "occupied" | "reserved" | "maintenance";

export type VehicleType = "car" | "bike" | "ev" | "other" | "motorcycle" | "bicycle" | "truck";

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

export interface UnifiedFacilityIntelligence {
  facility_id: number;
  total_slots: number;
  available_slots: number;
  occupied_slots: number;
  reserved_slots: number;
  current_occupancy_percentage: number;
  predicted_occupancy_percentage?: number;
  predicted_availability_probability?: number;
  expected_free_slots?: number;
  queue_wait_minutes?: number;
  recommendation?: string;
  occupancy_risk?: string;
  prediction_status: string;
  reasoning: string[];
}

export type ReservationStatus = "pending" | "confirmed" | "active" | "completed" | "cancelled" | "expired";

export interface ReservationCreateRequest {
  slot_id: number;
  reservation_start: string;
  reservation_end: string;
}

export interface Reservation {
  id: number;
  user_id: number;
  slot_id: number;
  reservation_start: string;
  reservation_end: string;
  status: ReservationStatus;
}

export interface EnrichedReservation extends Reservation {
  facilityName?: string;
  facilityAddress?: string;
  slotNumber?: string;
  zoneName?: string;
  vehicleType?: VehicleType;
}

export type ParkingSessionStatus = "active" | "completed" | "cancelled";

export interface SessionStartRequest {
  slot_id: number;
  reservation_id?: number;
}

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

export interface EnrichedSession extends ParkingSession {
  facilityName?: string;
  facilityAddress?: string;
  slotNumber?: string;
  zoneName?: string;
  vehicleType?: VehicleType;
}

export type PaymentMethod = "cash" | "card" | "upi" | "online" | "credit_card" | "debit_card" | "wallet";

export type PaymentStatus = "pending" | "success" | "failed" | "refunded" | "completed";

export interface PaymentProcessRequest {
  simulate_success?: boolean;
  transaction_id?: string;
  payment_method?: PaymentMethod;
}

export interface Payment {
  id: number;
  session_id: number;
  user_id: number;
  amount: number;
  payment_method: PaymentMethod;
  payment_status: PaymentStatus;
  transaction_id?: string | null;
  paid_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface EnrichedPayment extends Payment {
  facilityName?: string;
  slotNumber?: string;
  durationMinutes?: number;
}

export interface APIError {
  detail: string;
}

export interface WebSocketMessage {
  type: string;
  data: any;
}

// Realtime Parking Telemetry Events
export interface RealtimeSlotInfo {
  id: number;
  slot_number: string;
  zone_id: number;
  status: ParkingSlotStatus;
}

export interface RealtimeParkingSnapshotData {
  total_slots: number;
  available_slots: number;
  occupied_slots: number;
  reserved_slots: number;
  occupancy_percentage: number;
  slots: RealtimeSlotInfo[];
}

export interface ParkingSnapshotEvent {
  event: "parking_snapshot";
  facility_id: number;
  timestamp: string;
  data: RealtimeParkingSnapshotData;
}

export interface SlotStatusChangedEvent {
  event: "slot_status_changed";
  facility_id: number;
  zone_id: number;
  slot_id: number;
  slot_number: string;
  old_status: ParkingSlotStatus;
  new_status: ParkingSlotStatus;
  timestamp: string;
}

export interface RealtimeOccupancyData {
  total_slots: number;
  available_slots: number;
  occupied_slots: number;
  reserved_slots: number;
  occupancy_percentage: number;
}

export interface OccupancyUpdatedEvent {
  event: "occupancy_updated";
  facility_id: number;
  timestamp: string;
  data: RealtimeOccupancyData;
}

export type RealtimeParkingEvent =
  | ParkingSnapshotEvent
  | SlotStatusChangedEvent
  | OccupancyUpdatedEvent;
