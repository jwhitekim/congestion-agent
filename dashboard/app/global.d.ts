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

  // 드래그앤드롭된 항목에서 FileSystemHandle을 직접 얻는 확장 메서드
  // (File System Access API, Chromium 계열만 지원).
  interface DataTransferItem {
    getAsFileSystemHandle?(): Promise<FileSystemHandle>;
  }
}
