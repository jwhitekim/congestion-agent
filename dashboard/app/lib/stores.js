import { writable } from 'svelte/store';

// 사용자가 선택한 outputs/ 폴더의 FileSystemDirectoryHandle. null이면 아직 미선택.
export const outputsHandle = writable(null);

// outputsHandle 안의 세션 목록 (session.json 내용 + dirHandle이 합쳐진 객체 배열).
export const sessions = writable([]);

// 상세 화면에서 보고 있는 세션 객체 (sessions 배열의 항목 중 하나). null이면 목록 화면.
export const selectedSession = writable(null);
