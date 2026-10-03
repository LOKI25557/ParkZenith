import { useEffect, useState, useCallback, useMemo } from 'react';
import { wsService } from '../services/websocket';
import type { ConnectionStatus, RealtimeParkingEvent } from '../types';
import { useAuth } from './useAuth';

export const useWebSocket = (messageType: string = '*', facilityId?: number) => {
  const { token, isAuthenticated } = useAuth();
  const [latestMessage, setLatestMessage] = useState<RealtimeParkingEvent | any>(null);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>(wsService.status);
  const [lastMessageAt, setLastMessageAt] = useState<Date | null>(wsService.lastMessageAt);

  useEffect(() => {
    const unsubStatus = wsService.onStatusChange(setConnectionStatus);
    return () => unsubStatus();
  }, []);

  // Manage connection lifecycle only if facilityId is provided
  useEffect(() => {
    if (facilityId !== undefined) {
      if (isAuthenticated && token) {
        wsService.acquire(token, facilityId);
      } else {
        wsService.release();
      }

      return () => {
        wsService.release();
      };
    }
  }, [isAuthenticated, token, facilityId]);

  useEffect(() => {
    const handleMessage = (data: any) => {
      setLatestMessage(data);
      setLastMessageAt(new Date());
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
    if (facilityId !== undefined && token) {
      wsService.reconnect(token, facilityId);
    }
  }, [facilityId, token]);

  const isConnected = connectionStatus === 'connected';

  const isStale = useMemo(() => {
    return connectionStatus === 'disconnected' || connectionStatus === 'offline' || connectionStatus === 'unauthorized';
  }, [connectionStatus]);

  return {
    latestMessage,
    connectionStatus,
    isConnected,
    isStale,
    lastMessageAt,
    sendMessage,
    reconnect,
  };
};
