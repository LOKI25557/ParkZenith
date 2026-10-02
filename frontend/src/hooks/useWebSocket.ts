import { useEffect, useState } from 'react';
import { wsService } from '../services/websocket';
import { useAuth } from './useAuth';

export const useWebSocket = (messageType: string = '*') => {
  const { token, isAuthenticated } = useAuth();
  const [latestMessage, setLatestMessage] = useState<any>(null);

  useEffect(() => {
    if (isAuthenticated && token) {
      wsService.connect(token);
    }

    return () => {
      wsService.disconnect();
    };
  }, [isAuthenticated, token]);

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

  return { latestMessage, sendMessage };
};
