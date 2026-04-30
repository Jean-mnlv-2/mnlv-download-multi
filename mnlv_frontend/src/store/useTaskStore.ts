import { create } from 'zustand';
import axios from 'axios';
import toast from 'react-hot-toast';
import { LocalFileSystemService } from '../services/localFileSystem';

export type TaskStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';

export interface Task {
  id: string;
  status: TaskStatus;
  progress: number;
  message?: string;
  title?: string;
  original_url: string;
  provider: string;
  result_file?: string | null;
  result_file_url?: string | null;
  error_message?: string;
  media_type?: string;
  speed?: string;
  eta?: string;
  created_at?: string;
  save_to_dir?: string;
  track?: {
    title: string;
    artist: string;
    cover_url?: string | null;
    explicit?: boolean;
  };
}

export interface Notification {
  id: string;
  type: 'success' | 'error' | 'info' | 'warning';
  message: string;
}

interface TaskStore {
  tasks: Record<string, Task>;
  history: Task[];
  notifications: Notification[];
  refreshTrigger: number;
  stagedTracks: any[];
  localDirectorySelected: boolean;
  setLocalDirectorySelected: (selected: boolean) => void;
  setStagedTracks: (tracks: any[]) => void;
  triggerRefresh: () => void;
  addTask: (task: Task) => void;
  updateTask: (taskId: string, updates: Partial<Task>) => void;
  fetchHistory: () => Promise<void>;
  pollTaskStatus: (taskId: string) => void;
  clearCompleted: () => void;
  addNotification: (type: Notification['type'], message: string) => void;
  removeNotification: (id: string) => void;
  connectWebSocket: (token: string) => void;
  autoSaveToLocal: (taskId: string, taskData?: Task) => Promise<void>;
  cancelAllTasks: () => Promise<void>;
}

const STORAGE_KEY = 'mnlv_history_v2';

export const useTaskStore = create<TaskStore>((set, get) => ({
  tasks: {},
  history: [],
  notifications: [],
  refreshTrigger: 0,
  stagedTracks: [],
  localDirectorySelected: !!LocalFileSystemService.getHandle(),

  setLocalDirectorySelected: (selected) => set({ localDirectorySelected: selected }),
  setStagedTracks: (tracks) => set({ stagedTracks: tracks }),
  triggerRefresh: () => set((state) => ({ refreshTrigger: state.refreshTrigger + 1 })),
  
  fetchHistory: async () => {
    try {
      const response = await axios.get('/api/tasks/history/');
      const historyData = response.data;
      
      const newTasks = { ...get().tasks };
      historyData.forEach((task: Task) => {
        if (task.status === 'PROCESSING' || task.status === 'PENDING') {
          newTasks[task.id] = task;
        }
      });

      set({ 
        history: historyData,
        tasks: newTasks
      });
    } catch (error) {}
  },

  autoSaveToLocal: async (taskId: string, taskData?: Task) => {
    const task = taskData || get().tasks[taskId];
    if (!task || task.status !== 'COMPLETED') return;
    
    if (!LocalFileSystemService.getHandle()) return;

    try {
      const finalUrl = `/api/task/${taskId}/download/`;
      const token = localStorage.getItem('mnlv_access_token');
      
      const response = await fetch(finalUrl, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (!response.ok) return;
      
      const blob = await response.blob();
      
      const fileExtension = task.result_file?.split('.').pop() || 'mp3';
      let suggestedName = "";
      
      if (task.track && task.track.title && task.track.artist) {
        suggestedName = `${task.track.artist} - ${task.track.title}.${fileExtension}`;
      } else if (task.title && !task.title.includes('Téléchargement')) {
        suggestedName = `${task.title}.${fileExtension}`;
      } else {
        suggestedName = `download-${task.id.slice(0, 8)}.${fileExtension}`;
      }

      const saved = await LocalFileSystemService.saveFile(blob, suggestedName, task.save_to_dir);
      
      if (saved) {
        get().addNotification('success', `Enregistré : ${suggestedName}`);
      } else {
        get().addNotification('warning', "Autorisation locale requise.");
        set({ localDirectorySelected: false });
      }
    } catch (error) {}
  },

  cancelAllTasks: async () => {
    try {
      const response = await axios.post('/api/tasks/cancel-all/');
      if (response.data.status === 'success') {
        get().addNotification('info', response.data.message);
        await get().fetchHistory();
        
        set((state) => {
          const newTasks = { ...state.tasks };
          Object.keys(newTasks).forEach(id => {
            if (newTasks[id].status === 'PROCESSING' || newTasks[id].status === 'PENDING') {
              delete newTasks[id];
            }
          });
          return { tasks: newTasks };
        });
      }
    } catch (error) {}
  },

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
          message: data.message,
          error_message: data.error,
          result_file_url: data.result_file,
          speed: data.speed,
          eta: data.eta,
          track: data.track
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
    let shouldAutoSave = false;
    let shouldFetchHistory = false;
    
    set((state) => {
      const task = state.tasks[taskId];
      if (!task) return state;

      const updatedTask = { ...task, ...updates };
      
      if (updates.status === 'COMPLETED' && task.status !== 'COMPLETED') {
        const name = updatedTask.track ? `${updatedTask.track.title} - ${updatedTask.track.artist}` : 'Fichier';
        get().addNotification('success', `Téléchargement terminé : ${name}`);
        
        if (get().localDirectorySelected) {
          shouldAutoSave = true;
        }
      } else if (updates.status === 'FAILED' && task.status !== 'FAILED') {
        get().addNotification('error', `Échec du téléchargement : ${updatedTask.error_message || 'Erreur inconnue'}`);
      }

      const newTasks = { ...state.tasks, [taskId]: updatedTask };
      
      if (updates.status === 'COMPLETED' || updates.status === 'FAILED') {
        shouldFetchHistory = true;
      }

      return { tasks: newTasks };
    });

    if (shouldFetchHistory) {
      get().fetchHistory();
    }

    if (shouldAutoSave) {
      const taskAfterUpdate = get().tasks[taskId];
      get().autoSaveToLocal(taskId, taskAfterUpdate);
    }
  },

  pollTaskStatus: (taskId) => {
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
        get().updateTask(taskId, { status: 'FAILED', error_message: 'Erreur de connexion au serveur' });
        clearInterval(interval);
      }
    }, 2000);
  },

  clearCompleted: async () => {
    try {
      const response = await axios.post('/api/tasks/clear-history/');
      if (response.data.status === 'success') {
        get().addNotification('success', response.data.message);
        set((state) => {
          const newTasks = { ...state.tasks };
          Object.keys(newTasks).forEach(id => {
            if (newTasks[id].status === 'COMPLETED' || newTasks[id].status === 'FAILED') {
              delete newTasks[id];
            }
          });
          return { tasks: newTasks, history: [] };
        });
      }
    } catch (error) {
      get().addNotification('error', "Échec du vidage de l'historique");
    }
  },

  addNotification: (type, message) => {
    const id = Math.random().toString(36).substring(7);
    
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
