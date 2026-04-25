/**
 * Service pour gérer l'accès au système de fichiers local via la File System Access API.
 */
export class LocalFileSystemService {
  private static directoryHandle: FileSystemDirectoryHandle | null = null;
  private static readonly DB_NAME = 'mnlv_fs_db';
  private static readonly STORE_NAME = 'handles';
  private static readonly KEY = 'last_dir';

  static async initialize(): Promise<boolean> {
    try {
      const handle = await this.getStoredHandle();
      if (handle) {
        const options = { mode: 'readwrite' };
        if ((await (handle as any).queryPermission(options)) === 'granted') {
          this.directoryHandle = handle;
          return true;
        }
      }
      return false;
    } catch (e) {
      return false;
    }
  }

  /**
   * Demande à l'utilisateur de choisir un dossier de destination.
   */
  static async selectDirectory(): Promise<boolean> {
    if (!('showDirectoryPicker' in window)) {
      alert("Votre navigateur ne supporte pas l'accès au système de fichiers local. Utilisez Chrome ou Edge sur ordinateur.");
      return false;
    }

    try {
      const handle = await (window as any).showDirectoryPicker({
        mode: 'readwrite',
        id: 'mnlv_downloads'
      });
      
      this.directoryHandle = handle;
      await this.storeHandle(handle);
      return true;
    } catch (error: any) {
      if (error.name === 'AbortError') return false;
      alert(`Erreur : ${error.message}`);
      return false;
    }
  }

  private static async storeHandle(handle: FileSystemDirectoryHandle) {
    const db = await this.openDB();
    return new Promise<void>((resolve, reject) => {
      const tx = db.transaction(this.STORE_NAME, 'readwrite');
      const store = tx.objectStore(this.STORE_NAME);
      const request = store.put(handle, this.KEY);
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }

  private static async getStoredHandle(): Promise<FileSystemDirectoryHandle | null> {
    const db = await this.openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(this.STORE_NAME, 'readonly');
      const store = tx.objectStore(this.STORE_NAME);
      const request = store.get(this.KEY);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  private static openDB(): Promise<IDBDatabase> {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.DB_NAME, 1);
      request.onupgradeneeded = () => {
        request.result.createObjectStore(this.STORE_NAME);
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  static getHandle(): FileSystemDirectoryHandle | null {
    return this.directoryHandle;
  }

  static async hasPermission(request: boolean = false): Promise<boolean> {
    if (!this.directoryHandle) return false;
    
    const options = { mode: 'readwrite' };
    const currentPermission = await (this.directoryHandle as any).queryPermission(options);
    
    if (currentPermission === 'granted') {
      return true;
    }
    
    if (request && currentPermission === 'prompt') {
      try {
        if ((await (this.directoryHandle as any).requestPermission(options)) === 'granted') {
          return true;
        }
      } catch (e) {}
    }
    
    return false;
  }

  /**
   * Enregistre un fichier (Blob) dans le dossier sélectionné.
   * Crée des sous-dossiers si nécessaire (ex: pour une playlist).
   */
  static async saveFile(blob: Blob, fileName: string, subDirectoryName?: string, requestPerm: boolean = false): Promise<boolean> {
    try {
      if (!this.directoryHandle) {
        const restored = await this.initialize();
        if (!restored && !requestPerm) return false;
        if (!this.directoryHandle) return false;
      }

      const hasPerm = await this.hasPermission(requestPerm);
      if (!hasPerm) return false;

      let targetDir = this.directoryHandle;
      
      if (subDirectoryName) {
        const cleanSubDir = subDirectoryName.replace(/[<>:"/\\|?*]/g, '_').trim();
        targetDir = await this.directoryHandle.getDirectoryHandle(cleanSubDir, { create: true });
      }

      const cleanFileName = fileName.replace(/[<>:"/\\|?*]/g, '_').trim();
      const fileHandle = await targetDir.getFileHandle(cleanFileName, { create: true });
      const writable = await (fileHandle as any).createWritable();
      
      await writable.write(blob);
      await writable.close();
      
      return true;
    } catch (error: any) {
      return false;
    }
  }
}
