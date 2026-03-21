import { useEffect, useState } from 'react';

const SOCKET_URL = 'ws://localhost:8000/ws/scans';

export const useWebSockets = () => {
    const [lastScan, setLastScan] = useState<any>(null);
    const [isConnected, setIsConnected] = useState(false);

    useEffect(() => {
        const socket = new WebSocket(SOCKET_URL);

        socket.onopen = () => {
            console.log('WebSocket Connected');
            setIsConnected(true);
        };

        socket.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                if (message.type === 'NEW_SCAN') {
                    setLastScan(message.data);
                }
            } catch (err) {
                console.error('WebSocket message error:', err);
            }
        };

        socket.onclose = () => {
            console.log('WebSocket Disconnected');
            setIsConnected(false);
        };

        return () => {
            socket.close();
        };
    }, []);

    return { lastScan, isConnected };
};
