type MessageHandler = (data: any) => void;
export type ConnectionStatus = 'connected' | 'connecting' | 'disconnected' | 'reconnecting' | 'unauthorized';
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

  public connect(token?: string, facilityId?: number) {
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
          const message = JSON.parse(event.data);
          const eventType = message.event || message.type;
          const payload = message.data !== undefined ? message.data : message;

          if (eventType && this.handlers.has(eventType)) {
            this.handlers.get(eventType)?.forEach((handler) => handler(payload));
          }

          // Wildcard dispatch
          if (this.handlers.has('*')) {
            this.handlers.get('*')?.forEach((handler) => handler(message));
          }
        } catch (error) {
          console.error('WebSocket message parsing error:', error);
        }
      };

      this.ws.onclose = (ev) => {
        if (ev.code === 1008) {
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
    this.connect(token, facilityId);
  }

  public disconnect() {
    if (this.reconnectTimeoutId) {
      clearTimeout(this.reconnectTimeoutId);
      this.reconnectTimeoutId = null;
    }
    if (this.ws) {
      this.ws.onclose = null;
      this.ws.onerror = null;
      this.ws.close();
      this.ws = null;
    }
    this.reconnectAttempts = 0;
    this.setStatus('disconnected');
  }

  private attemptReconnect() {
    if (!this.token) {
      this.setStatus('unauthorized');
      return;
    }
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      this.setStatus('reconnecting');
      this.reconnectTimeoutId = setTimeout(() => {
        this.connect();
      }, this.reconnectDelay * this.reconnectAttempts);
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
