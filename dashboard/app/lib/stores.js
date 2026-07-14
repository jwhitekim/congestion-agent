import { writable } from 'svelte/store';

// 고정 루트(outputs/)에서 읽어온 세션 목록 (session.json 내용 배열).
export const sessions = writable([]);

// 상세 화면에서 보고 있는 세션 객체 (sessions 배열의 항목 중 하나). null이면 목록 화면.
export const selectedSession = writable(null);
