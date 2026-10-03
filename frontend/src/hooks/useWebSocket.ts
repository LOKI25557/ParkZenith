import { useEffect, useState } from 'react';
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
    if (isAuthenticated && token) {
      wsService.connect(token, facilityId);
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

  const sendMessage = (message: any) => {
    wsService.send(message);
  };

  return { latestMessage, connectionStatus, sendMessage };
};
