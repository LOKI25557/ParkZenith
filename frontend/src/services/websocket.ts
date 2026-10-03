import type { ConnectionStatus, RealtimeParkingEvent } from '../types';

export type { ConnectionStatus };

type MessageHandler = (data: any) => void;
type StatusListener = (status: ConnectionStatus) => void;

export class WebSocketService {
  private ws: WebSocket | null = null;
  private baseUrl: string;
  private handlers: Map<string, MessageHandler[]> = new Map();
  private statusListeners: Set<StatusListener> = new Set();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 2000;
  private token: string | null = null;
  private currentFacilityId?: number;
  private _status: ConnectionStatus = 'disconnected';
  private reconnectTimeoutId: any = null;
  private disconnectTimeoutId: any = null;
  private activeSubscribers = 0;
  private lastMessageTimestamp: Date | null = null;

  constructor() {
    this.baseUrl = import.meta.env.VITE_WS_URL || 'ws://127.0.0.1:8000';
    try {
      this.token = localStorage.getItem('parkzenith_token');
    } catch {
      this.token = null;
    }
  }

  public get status(): ConnectionStatus {
    return this._status;
  }

  public get facilityId(): number | undefined {
    return this.currentFacilityId;
  }

  public get lastMessageAt(): Date | null {
    return this.lastMessageTimestamp;
  }

  private setStatus(newStatus: ConnectionStatus) {
    this._status = newStatus;
    this.statusListeners.forEach((listener) => listener(newStatus));
  }

  public onStatusChange(listener: StatusListener) {
    this.statusListeners.add(listener);
    listener(this._status);
    return () => {
      this.statusListeners.delete(listener);
    };
  }

  /**
   * Acquire a connection for a facility with reference counting.
   */
  public acquire(token?: string, facilityId?: number) {
    if (this.disconnectTimeoutId) {
      clearTimeout(this.disconnectTimeoutId);
      this.disconnectTimeoutId = null;
    }

    if (facilityId !== undefined) {
      if (this.currentFacilityId !== facilityId) {
        // Switching to a different facility -> reset subscriber count for the new facility
        this.activeSubscribers = 1;
        this.connect(token, facilityId, true);
        return;
      }
    }

    this.activeSubscribers++;
    this.connect(token, facilityId, false);
  }

  /**
   * Release a connection with reference counting and grace period.
   */
  public release() {
    this.activeSubscribers = Math.max(0, this.activeSubscribers - 1);
    if (this.activeSubscribers === 0) {
      // Small grace period (300ms) to allow page transitions without tearing down socket
      if (this.disconnectTimeoutId) {
        clearTimeout(this.disconnectTimeoutId);
      }
      this.disconnectTimeoutId = setTimeout(() => {
        if (this.activeSubscribers === 0) {
          this.disconnect();
        }
        this.disconnectTimeoutId = null;
      }, 300);
    }
  }

  public connect(token?: string, facilityId?: number, force = false) {
    if (token !== undefined) {
      this.token = token;
    } else {
      try {
        this.token = localStorage.getItem('parkzenith_token');
      } catch {
        this.token = null;
      }
    }

    if (facilityId !== undefined) {
      this.currentFacilityId = facilityId;
    }

    // Clear any pending reconnect
    if (this.reconnectTimeoutId) {
      clearTimeout(this.reconnectTimeoutId);
      this.reconnectTimeoutId = null;
    }

    if (!this.currentFacilityId) {
      this.setStatus('disconnected');
      return;
    }

    if (!this.token) {
      this.setStatus('unauthorized');
      return;
    }

    // Deduplication: if already OPEN or CONNECTING for this facility, preserve it
    if (
      !force &&
      this.ws &&
      (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    // Close any prior connection
    if (this.ws) {
      this.ws.onclose = null;
      this.ws.onerror = null;
      this.ws.close();
      this.ws = null;
    }

    this.setStatus('connecting');

    // Real backend WebSocket endpoint: /ws/parking/{facility_id}?token={token}
    const endpoint = `${this.baseUrl}/ws/parking/${this.currentFacilityId}?token=${encodeURIComponent(this.token)}`;

    try {
      this.ws = new WebSocket(endpoint);

      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        this.setStatus('connected');
      };

      this.ws.onmessage = (event) => {
        try {
          this.lastMessageTimestamp = new Date();
          const message: RealtimeParkingEvent = JSON.parse(event.data);
          const eventType = (message as any).event || (message as any).type;
          const payload = (message as any).data !== undefined ? (message as any).data : message;

          if (eventType && this.handlers.has(eventType)) {
            this.handlers.get(eventType)?.forEach((handler) => handler(payload));
          }

          // Wildcard dispatch passes the full parsed envelope
          if (this.handlers.has('*')) {
            this.handlers.get('*')?.forEach((handler) => handler(message));
          }
        } catch (error) {
          console.error('WebSocket message parsing error:', error);
        }
      };

      this.ws.onclose = (ev) => {
        if (ev.code === 1008) {
          // 1008 Policy Violation (Unauthorized or Facility Not Found): do not spam reconnect
          this.setStatus('unauthorized');
        } else {
          this.setStatus('disconnected');
          this.attemptReconnect();
        }
      };

      this.ws.onerror = () => {
        this.setStatus('disconnected');
      };
    } catch {
      this.setStatus('disconnected');
    }
  }

  public reconnect(token?: string, facilityId?: number) {
    this.reconnectAttempts = 0;
    this.connect(token, facilityId, true);
  }

  public disconnect() {
    if (this.reconnectTimeoutId) {
      clearTimeout(this.reconnectTimeoutId);
      this.reconnectTimeoutId = null;
    }
    if (this.disconnectTimeoutId) {
      clearTimeout(this.disconnectTimeoutId);
      this.disconnectTimeoutId = null;
    }
    if (this.ws) {
      this.ws.onclose = null;
      this.ws.onerror = null;
      this.ws.close();
      this.ws = null;
    }
    this.reconnectAttempts = 0;
    this.activeSubscribers = 0;
    this.setStatus('disconnected');
  }

  private attemptReconnect() {
    if (!this.token || this._status === 'unauthorized') {
      this.setStatus('unauthorized');
      return;
    }
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      this.setStatus('reconnecting');
      this.reconnectTimeoutId = setTimeout(() => {
        this.connect();
      }, this.reconnectDelay * this.reconnectAttempts);
    } else {
      this.setStatus('offline');
    }
  }

  public subscribe(type: string, handler: MessageHandler) {
    if (!this.handlers.has(type)) {
      this.handlers.set(type, []);
    }
    this.handlers.get(type)?.push(handler);

    return () => this.unsubscribe(type, handler);
  }

  public unsubscribe(type: string, handler: MessageHandler) {
    if (this.handlers.has(type)) {
      const filtered = this.handlers.get(type)?.filter((h) => h !== handler) || [];
      this.handlers.set(type, filtered);
    }
  }

  public send(message: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }
}

export const wsService = new WebSocketService();
