import { create } from 'zustand';
import axios from 'axios';
import toast from 'react-hot-toast';

export type TaskStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';

export interface Task {
  id: string;
  status: TaskStatus;
  progress: number;
  original_url: string;
  provider: string;
  result_file?: string | null;
  result_file_url?: string | null;
  error_message?: string;
  track?: {
    title: string;
    artist: string;
    cover_url?: string | null;
  };
}

export interface Notification {
  id: string;
  type: 'success' | 'error' | 'info';
  message: string;
}

interface TaskStore {
  tasks: Record<string, Task>;
  history: string[];
  notifications: Notification[];
  addTask: (task: Task) => void;
  updateTask: (taskId: string, updates: Partial<Task>) => void;
  pollTaskStatus: (taskId: string) => void;
  clearCompleted: () => void;
  addNotification: (type: Notification['type'], message: string) => void;
  removeNotification: (id: string) => void;
  connectWebSocket: (token: string) => void;
}

const STORAGE_KEY = 'mnlv_history_v2';

export const useTaskStore = create<TaskStore>((set, get) => ({
  tasks: {},
  history: JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'),
  notifications: [],
  
  connectWebSocket: (token) => {
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const wsUrl = `${protocol}://${window.location.host}/ws/tasks/?token=${token}`;
    const socket = new WebSocket(wsUrl);

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.task_id) {
        get().updateTask(data.task_id, {
          status: data.status,
          progress: data.progress,
          error_message: data.error,
          result_file_url: data.result_file
        });
      }
    };

    socket.onclose = () => {
      setTimeout(() => get().connectWebSocket(token), 5000);
    };
  },
  
  addTask: (task) => {
    set((state) => ({
      tasks: { ...state.tasks, [task.id]: task }
    }));
  },

  updateTask: (taskId, updates) => {
    set((state) => {
      const task = state.tasks[taskId];
      if (!task) return state;

      const updatedTask = { ...task, ...updates };
      
      if (updates.status === 'COMPLETED' && task.status !== 'COMPLETED') {
        get().addNotification('success', `Téléchargement terminé : ${updatedTask.track?.title || 'Fichier'}`);
      } else if (updates.status === 'FAILED' && task.status !== 'FAILED') {
        get().addNotification('error', `Échec du téléchargement : ${updatedTask.error_message || 'Erreur inconnue'}`);
      }

      const newTasks = { ...state.tasks, [taskId]: updatedTask };
      
      if (updates.status === 'COMPLETED' || updates.status === 'FAILED') {
        const newHistory = [...new Set([taskId, ...state.history])].slice(0, 50);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(newHistory));
        return { tasks: newTasks, history: newHistory };
      }

      return { tasks: newTasks };
    });
  },

  pollTaskStatus: (taskId) => {
    // Si WebSocket est actif, on peut ignorer le polling ou l'utiliser en fallback
    const interval = setInterval(async () => {
      try {
        const response = await axios.get(`/api/task/${taskId}/status/`);
        const taskData = response.data;
        
        get().updateTask(taskId, {
          status: taskData.status,
          progress: taskData.progress,
          result_file: taskData.result_file,
          result_file_url: taskData.result_file_url,
          error_message: taskData.error_message,
          track: taskData.track
        });

        if (taskData.status === 'COMPLETED' || taskData.status === 'FAILED') {
          clearInterval(interval);
        }
      } catch (error) {
        console.error('Polling error:', error);
        get().updateTask(taskId, { status: 'FAILED', error_message: 'Erreur de connexion au serveur' });
        clearInterval(interval);
      }
    }, 2000);
  },

  clearCompleted: () => {
    set((state) => {
      const newTasks = { ...state.tasks };
      Object.keys(newTasks).forEach(id => {
        if (newTasks[id].status === 'COMPLETED' || newTasks[id].status === 'FAILED') {
          delete newTasks[id];
        }
      });
      return { tasks: newTasks };
    });
  },

  addNotification: (type, message) => {
    const id = Math.random().toString(36).substring(7);
    
    // Toast notification
    if (type === 'success') toast.success(message);
    else if (type === 'error') toast.error(message);
    else toast(message);

    set((state) => ({
      notifications: [{ id, type, message }, ...state.notifications].slice(0, 5)
    }));
    setTimeout(() => get().removeNotification(id), 5000);
  },

  removeNotification: (id) => {
    set((state) => ({
      notifications: state.notifications.filter(n => n.id !== id)
    }));
  }
}));
