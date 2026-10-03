import React, { createContext, useContext, useEffect, useState, useMemo } from 'react';
import type { ConnectionStatus, RealtimeParkingEvent } from '../types';
import { useWebSocket } from '../hooks/useWebSocket';

export interface ParkingRealtimeContextType {
  facilityId?: number;
  connectionStatus: ConnectionStatus;
  isConnected: boolean;
  isStale: boolean;
  latestMessage: RealtimeParkingEvent | null;
  lastMessageAt: Date | null;
  recentlyUpdatedSlotIds: Set<number>;
  reconnect: () => void;
  sendMessage: (msg: any) => void;
}

const ParkingRealtimeContext = createContext<ParkingRealtimeContextType | null>(null);

export interface ParkingRealtimeProviderProps {
  facilityId?: number;
  children: React.ReactNode;
}

export const ParkingRealtimeProvider: React.FC<ParkingRealtimeProviderProps> = ({
  facilityId,
  children,
}) => {
  const { latestMessage, connectionStatus, isConnected, isStale, lastMessageAt, reconnect, sendMessage } =
    useWebSocket('*', facilityId);

  const [recentlyUpdatedSlotIds, setRecentlyUpdatedSlotIds] = useState<Set<number>>(new Set());

  // Track slot status changes to pulse recently updated bays
  useEffect(() => {
    if (!latestMessage) return;

    if (latestMessage.event === 'slot_status_changed' && latestMessage.slot_id) {
      const slotId = latestMessage.slot_id;
      setRecentlyUpdatedSlotIds((prev) => {
        const next = new Set(prev);
        next.add(slotId);
        return next;
      });

      const timer = setTimeout(() => {
        setRecentlyUpdatedSlotIds((prev) => {
          const next = new Set(prev);
          next.delete(slotId);
          return next;
        });
      }, 1600);

      return () => clearTimeout(timer);
    }
  }, [latestMessage]);

  const value = useMemo(
    () => ({
      facilityId,
      connectionStatus,
      isConnected,
      isStale,
      latestMessage,
      lastMessageAt,
      recentlyUpdatedSlotIds,
      reconnect,
      sendMessage,
    }),
    [
      facilityId,
      connectionStatus,
      isConnected,
      isStale,
      latestMessage,
      lastMessageAt,
      recentlyUpdatedSlotIds,
      reconnect,
      sendMessage,
    ]
  );

  return (
    <ParkingRealtimeContext.Provider value={value}>
      {children}
    </ParkingRealtimeContext.Provider>
  );
};

export const useParkingRealtime = (): ParkingRealtimeContextType | null => {
  return useContext(ParkingRealtimeContext);
};
