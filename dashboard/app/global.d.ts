// File System Access API는 아직 표준 DOM lib 타입에 없어 별도로 선언한다.
export {};

declare global {
  interface Window {
    showDirectoryPicker(options?: {
      id?: string;
      mode?: 'read' | 'readwrite';
      startIn?: string;
    }): Promise<FileSystemDirectoryHandle>;
  }
}
