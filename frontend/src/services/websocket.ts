type MessageHandler = (data: any) => void;
export type ConnectionStatus = 'connected' | 'connecting' | 'disconnected' | 'reconnecting';
type StatusListener = (status: ConnectionStatus) => void;

export class WebSocketService {
  private ws: WebSocket | null = null;
  private baseUrl: string;
  private handlers: Map<string, MessageHandler[]> = new Map();
  private statusListeners: Set<StatusListener> = new Set();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 2000;
  private token: string | null;
  private currentFacilityId?: number;
  private _status: ConnectionStatus = 'disconnected';

  constructor() {
    this.baseUrl = import.meta.env.VITE_WS_URL || 'ws://127.0.0.1:8000';
    this.token = localStorage.getItem('parkzenith_token');
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
    if (token) {
      this.token = token;
    } else {
      this.token = localStorage.getItem('parkzenith_token');
    }

    if (facilityId !== undefined) {
      this.currentFacilityId = facilityId;
    }

    if (!this.token) {
      this.setStatus('disconnected');
      return;
    }

    // Close any prior connection
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this.setStatus('connecting');

    // Connect to facility endpoint if facilityId provided, or general ws
    const endpoint = this.currentFacilityId
      ? `${this.baseUrl}/api/ws/parking/${this.currentFacilityId}?token=${this.token}`
      : `${this.baseUrl}/api/ws?token=${this.token}`;

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

      this.ws.onclose = () => {
        this.setStatus('disconnected');
        this.attemptReconnect();
      };

      this.ws.onerror = () => {
        this.setStatus('disconnected');
      };
    } catch {
      this.setStatus('disconnected');
    }
  }

  public disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.setStatus('disconnected');
  }

  private attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      this.setStatus('reconnecting');
      setTimeout(() => {
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
