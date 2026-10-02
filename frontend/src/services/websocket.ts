type MessageHandler = (data: any) => void;

export class WebSocketService {
  private ws: WebSocket | null = null;
  private url: string;
  private handlers: Map<string, MessageHandler[]> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 2000;
  private token: string | null;

  constructor() {
    const baseUrl = import.meta.env.VITE_WS_URL || 'ws://127.0.0.1:8000';
    this.url = `${baseUrl}/api/ws`;
    this.token = localStorage.getItem('parkzenith_token');
  }

  public connect(token?: string) {
    if (token) {
      this.token = token;
    }

    if (!this.token) {
      console.warn("WebSocket connection requires authentication token");
      return;
    }

    // Usually WebSocket auth is passed via query params or a first auth message
    const wsUrl = `${this.url}?token=${this.token}`;
    
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('WebSocket Connected');
      this.reconnectAttempts = 0;
    };

    this.ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        const { type, data } = message;
        
        if (type && this.handlers.has(type)) {
          this.handlers.get(type)?.forEach(handler => handler(data));
        }
        
        // Also trigger wildcard handler if any
        if (this.handlers.has('*')) {
          this.handlers.get('*')?.forEach(handler => handler(message));
        }
      } catch (error) {
        console.error('WebSocket message parsing error', error);
      }
    };

    this.ws.onclose = () => {
      console.log('WebSocket Disconnected');
      this.attemptReconnect();
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket Error', error);
    };
  }

  public disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  private attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => {
        console.log(`Reconnecting WebSocket (Attempt ${this.reconnectAttempts})...`);
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
      const filtered = this.handlers.get(type)?.filter(h => h !== handler) || [];
      this.handlers.set(type, filtered);
    }
  }

  public send(message: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not open. Cannot send message');
    }
  }
}

export const wsService = new WebSocketService();
