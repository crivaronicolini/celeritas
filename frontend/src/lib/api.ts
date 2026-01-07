const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

async function fetchAPI<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || 'Request failed');
  }

  return response.json();
}

// Auth
export async function getCurrentUser() {
  return fetchAPI<User>('/users/me');
}

export async function logout() {
  return fetchAPI('/auth/jwt/logout', { method: 'POST' });
}

export async function getGoogleAuthUrl(): Promise<string> {
  const response = await fetchAPI<{ authorization_url: string }>('/auth/google/authorize');
  return response.authorization_url;
}

export async function debugLogin(): Promise<{ message: string; email: string }> {
  return fetchAPI('/auth/debug-login', { method: 'POST' });
}

export async function checkDebugMode(): Promise<boolean> {
  try {
    await fetchAPI('/auth/debug-status');
    return true;
  } catch {
    return false;
  }
}

// Conversations
export async function getConversations() {
  return fetchAPI<ConversationList>('/conversations/');
}

export async function createConversation(title?: string) {
  return fetchAPI<Conversation>('/conversations/', {
    method: 'POST',
    body: JSON.stringify(title ? { title } : {}),
  });
}

export async function getConversation(id: string) {
  return fetchAPI<Conversation>(`/conversations/${id}`);
}

export async function getConversationMessages(id: string) {
  return fetchAPI<Message[]>(`/conversations/${id}/messages`);
}

export async function deleteConversation(id: string) {
  return fetchAPI(`/conversations/${id}`, { method: 'DELETE' });
}

export async function updateConversation(id: string, title: string) {
  return fetchAPI<Conversation>(`/conversations/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ title }),
  });
}

// Chat
export async function sendMessage(conversationId: string, question: string) {
  return fetchAPI<MessageResponse>(`/chat/message/${conversationId}`, {
    method: 'POST',
    body: JSON.stringify({ question }),
  });
}

export async function submitFeedback(interactionId: number, isPositive: boolean) {
  return fetchAPI('/chat/feedback', {
    method: 'POST',
    body: JSON.stringify({ interaction_id: interactionId, is_positive: isPositive }),
  });
}

// Documents
export async function getDocuments() {
  return fetchAPI<Document[]>('/documents/');
}

export async function uploadDocuments(files: File[]) {
  const formData = new FormData();
  files.forEach((file) => formData.append('files', file));

  const response = await fetch(`${API_BASE}/documents/`, {
    method: 'POST',
    credentials: 'include',
    body: formData,
  });

  if (!response.ok) {
    throw new Error('Upload failed');
  }

  return response.json() as Promise<UploadResponse>;
}

export async function deleteAllDocuments() {
  return fetchAPI<Document[]>('/documents/', { method: 'DELETE' });
}

// Analytics (admin only)
export async function getAnalytics() {
  return fetchAPI<Analytics>('/analytics/');
}

export async function getRecentInteractions(limit = 10) {
  return fetchAPI<Interaction[]>(`/analytics/interactions/recent?limit=${limit}`);
}

export async function getUnusedDocuments() {
  return fetchAPI<Document[]>('/analytics/documents/unused');
}

export async function getUnansweredPatterns() {
  return fetchAPI<UnansweredPatterns>('/analytics/questions/unanswered-patterns');
}

// Types
export interface User {
  id: string;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
  is_verified: boolean;
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationList {
  conversations: Conversation[];
}

export interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export interface Document {
  id: number;
  filename: string;
  uploaded_at: string;
}

export interface MessageResponse {
  answer: string;
  interaction_id: number | null;
  source_documents: Document[];
}

export interface UploadResponse {
  successful_uploads: Document[];
  failed_uploads: { filename: string; error: string }[];
}

export interface Analytics {
  most_frequently_queried_documents: { filename: string; query_count: number }[];
  most_often_asked_questions: { question: string; ask_count: number }[];
  weekly_queries_per_document: { filename: string; weekly_query_count: number }[];
  average_response_time_seconds: number;
  feedback_statistics: {
    total_feedback_count: number;
    positive_feedback_count: number;
    negative_feedback_count: number;
    positive_feedback_percentage: number;
  };
  total_interactions: number;
}

export interface Interaction {
  id: number;
  question: string;
  answer: string;
  timestamp: string;
  response_time: number;
  used_documents: string[];
}

export interface UnansweredPatterns {
  questions_without_documents: {
    id: number;
    question: string;
    answer: string;
    timestamp: string;
  }[];
  questions_with_negative_feedback: {
    id: number;
    question: string;
    answer: string;
    timestamp: string;
  }[];
}
