import { useEffect, useState, useCallback } from 'react';
import { wsService } from '../services/websocket';
import type { ConnectionStatus } from '../services/websocket';
import { useAuth } from './useAuth';

export const useWebSocket = (messageType: string = '*', facilityId?: number) => {
  const { token, isAuthenticated } = useAuth();
  const [latestMessage, setLatestMessage] = useState<any>(null);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>(wsService.status);

  useEffect(() => {
    const unsubStatus = wsService.onStatusChange(setConnectionStatus);
    return () => unsubStatus();
  }, []);

  useEffect(() => {
    if (facilityId !== undefined) {
      if (isAuthenticated && token) {
        wsService.connect(token, facilityId);
      } else {
        wsService.disconnect();
      }
    }

    return () => {
      wsService.disconnect();
    };
  }, [isAuthenticated, token, facilityId]);

  useEffect(() => {
    const handleMessage = (data: any) => {
      setLatestMessage(data);
    };

    const unsubscribe = wsService.subscribe(messageType, handleMessage);

    return () => {
      unsubscribe();
    };
  }, [messageType]);

  const sendMessage = useCallback((message: any) => {
    wsService.send(message);
  }, []);

  const reconnect = useCallback(() => {
    if (facilityId && token) {
      wsService.reconnect(token, facilityId);
    }
  }, [facilityId, token]);

  return {
    latestMessage,
    connectionStatus,
    isConnected: connectionStatus === 'connected',
    sendMessage,
    reconnect,
  };
};
