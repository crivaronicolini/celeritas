import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ChatContainerRoot,
  ChatContainerContent,
} from '@/components/ui/chat-container';
import { Message, MessageContent } from '@/components/ui/message';
import {
  PromptInput,
  PromptInputTextarea,
  PromptInputActions,
  PromptInputAction,
} from '@/components/ui/prompt-input';
import { ScrollButton } from '@/components/ui/scroll-button';
import { Loader } from '@/components/ui/loader';
import { FileUpload, FileUploadTrigger } from '@/components/ui/file-upload';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/context/AuthContext';
import {
  getConversations,
  createConversation,
  getConversationMessages,
  sendMessage,
  deleteConversation,
  updateConversation,
  uploadDocuments,
  submitFeedback,
  type Conversation,
  type Message as ApiMessage,
  type MessageResponse,
} from '@/lib/api';

interface ChatMessage extends ApiMessage {
  interactionId?: number | null;
  sourceDocuments?: string[];
  isLoading?: boolean;
}

export function ChatPage() {
  const { user } = useAuth();
  const { conversationId } = useParams<{ conversationId?: string }>();
  const navigate = useNavigate();

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');

  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadConversations = useCallback(async () => {
    try {
      const data = await getConversations();
      setConversations(data.conversations);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  }, []);

  const loadMessages = useCallback(async (convId: string) => {
    setIsLoading(true);
    try {
      const data = await getConversationMessages(convId);
      setMessages(data);
    } catch (error) {
      console.error('Failed to load messages:', error);
      setMessages([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (user) {
      loadConversations();
    }
  }, [user, loadConversations]);

  useEffect(() => {
    if (conversationId) {
      loadMessages(conversationId);
    } else {
      setMessages([]);
    }
  }, [conversationId, loadMessages]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === 'u') {
        e.preventDefault();
        fileInputRef.current?.click();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleNewConversation = async () => {
    try {
      const conv = await createConversation();
      setConversations((prev) => [conv, ...prev]);
      navigate(`/chat/${conv.id}`);
    } catch (error) {
      console.error('Failed to create conversation:', error);
    }
  };

  const handleDeleteConversation = async (id: string) => {
    try {
      await deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (conversationId === id) {
        navigate('/');
      }
    } catch (error) {
      console.error('Failed to delete conversation:', error);
    }
  };

  const handleRenameConversation = async (id: string) => {
    if (!editingTitle.trim()) return;
    try {
      const updated = await updateConversation(id, editingTitle);
      setConversations((prev) =>
        prev.map((c) => (c.id === id ? { ...c, title: updated.title } : c))
      );
      setEditingId(null);
      setEditingTitle('');
    } catch (error) {
      console.error('Failed to rename conversation:', error);
    }
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isSending) return;

    let activeConversationId = conversationId;

    if (!activeConversationId) {
      try {
        const conv = await createConversation(inputValue.slice(0, 50));
        setConversations((prev) => [conv, ...prev]);
        activeConversationId = conv.id;
        navigate(`/chat/${conv.id}`, { replace: true });
      } catch (error) {
        console.error('Failed to create conversation:', error);
        return;
      }
    }

    const userMessage: ChatMessage = { role: 'user', content: inputValue };
    const loadingMessage: ChatMessage = {
      role: 'assistant',
      content: '',
      isLoading: true,
    };

    setMessages((prev) => [...prev, userMessage, loadingMessage]);
    setInputValue('');
    setIsSending(true);

    try {
      const response: MessageResponse = await sendMessage(
        activeConversationId,
        userMessage.content
      );

      setMessages((prev) => {
        const newMessages = prev.slice(0, -1);
        return [
          ...newMessages,
          {
            role: 'assistant' as const,
            content: response.answer,
            interactionId: response.interaction_id,
            sourceDocuments: response.source_documents.map((d) => d.filename),
          },
        ];
      });
    } catch (error) {
      console.error('Failed to send message:', error);
      setMessages((prev) => {
        const newMessages = prev.slice(0, -1);
        return [
          ...newMessages,
          {
            role: 'assistant' as const,
            content: 'Sorry, an error occurred. Please try again.',
          },
        ];
      });
    } finally {
      setIsSending(false);
    }
  };

  const handleFeedback = async (interactionId: number, isPositive: boolean) => {
    try {
      await submitFeedback(interactionId, isPositive);
    } catch (error) {
      console.error('Failed to submit feedback:', error);
    }
  };

  const handleFilesAdded = async (files: File[]) => {
    const pdfFiles = files.filter((f) => f.type === 'application/pdf');
    if (pdfFiles.length === 0) {
      alert('Only PDF files are supported');
      return;
    }

    try {
      const result = await uploadDocuments(pdfFiles);
      if (result.successful_uploads.length > 0) {
        alert(`Uploaded ${result.successful_uploads.length} document(s)`);
      }
      if (result.failed_uploads.length > 0) {
        alert(
          `Failed to upload: ${result.failed_uploads.map((f) => f.filename).join(', ')}`
        );
      }
    } catch (error) {
      console.error('Upload failed:', error);
      alert('Upload failed');
    }
  };

  if (!user) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-3.5rem)]">
        <div className="text-center">
          <h2 className="text-xl font-medium mb-2">Welcome to Celeritas</h2>
          <p className="text-muted-foreground">
            Sign in to start chatting with your documents
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-3.5rem)]">
      {/* Sidebar */}
      <aside className="w-64 border-r border-border bg-card flex flex-col">
        <div className="p-3 border-b border-border">
          <Button onClick={handleNewConversation} className="w-full" size="sm">
            + New Chat
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto">
          {conversations.map((conv) => (
            <div
              key={conv.id}
              className={`group flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-accent ${
                conversationId === conv.id ? 'bg-accent' : ''
              }`}
              onClick={() => navigate(`/chat/${conv.id}`)}
            >
              {editingId === conv.id ? (
                <input
                  type="text"
                  value={editingTitle}
                  onChange={(e) => setEditingTitle(e.target.value)}
                  onBlur={() => handleRenameConversation(conv.id)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleRenameConversation(conv.id);
                    if (e.key === 'Escape') setEditingId(null);
                  }}
                  onClick={(e) => e.stopPropagation()}
                  className="flex-1 bg-background px-1 text-sm rounded"
                  autoFocus
                />
              ) : (
                <span className="flex-1 text-sm truncate">{conv.title}</span>
              )}
              <div className="hidden group-hover:flex items-center gap-1">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setEditingId(conv.id);
                    setEditingTitle(conv.title);
                  }}
                  className="text-xs text-muted-foreground hover:text-foreground"
                >
                  ✏️
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteConversation(conv.id);
                  }}
                  className="text-xs text-muted-foreground hover:text-destructive"
                >
                  🗑️
                </button>
              </div>
            </div>
          ))}
        </div>
      </aside>

      {/* Chat Area */}
      <div className="flex-1 flex flex-col">
        <FileUpload onFilesAdded={handleFilesAdded} accept=".pdf">
          <div className="flex-1 relative">
            <ChatContainerRoot className="h-full">
              <ChatContainerContent className="p-4 space-y-4">
                {isLoading ? (
                  <div className="flex justify-center py-8">
                    <Loader variant="dots" />
                  </div>
                ) : messages.length === 0 ? (
                  <div className="flex items-center justify-center h-full text-muted-foreground">
                    <div className="text-center">
                      <p className="text-lg mb-2">Start a conversation</p>
                      <p className="text-sm">
                        Ask questions about your uploaded documents
                      </p>
                    </div>
                  </div>
                ) : (
                  messages.map((msg, idx) => (
                    <Message key={idx}>
                      <MessageContent
                        markdown={msg.role === 'assistant' && !msg.isLoading}
                        className={
                          msg.role === 'user'
                            ? 'bg-primary text-primary-foreground ml-auto max-w-[80%] rounded-lg p-3'
                            : 'bg-muted max-w-[80%] rounded-lg p-3'
                        }
                      >
                        {msg.isLoading ? (
                          <Loader variant="typing" size="sm" />
                        ) : (
                          msg.content
                        )}
                      </MessageContent>
                      {msg.role === 'assistant' &&
                        !msg.isLoading &&
                        msg.sourceDocuments &&
                        msg.sourceDocuments.length > 0 && (
                          <div className="text-xs text-muted-foreground mt-1">
                            Sources: {msg.sourceDocuments.join(', ')}
                          </div>
                        )}
                      {msg.role === 'assistant' &&
                        !msg.isLoading &&
                        msg.interactionId && (
                          <div className="flex gap-2 mt-1">
                            <button
                              onClick={() =>
                                handleFeedback(msg.interactionId!, true)
                              }
                              className="text-xs text-muted-foreground hover:text-green-500"
                            >
                              👍
                            </button>
                            <button
                              onClick={() =>
                                handleFeedback(msg.interactionId!, false)
                              }
                              className="text-xs text-muted-foreground hover:text-red-500"
                            >
                              👎
                            </button>
                          </div>
                        )}
                    </Message>
                  ))
                )}
              </ChatContainerContent>
              <div className="absolute bottom-20 right-4">
                <ScrollButton />
              </div>
            </ChatContainerRoot>
          </div>

          {/* Input Area */}
          <div className="border-t border-border p-4 bg-card">
            <PromptInput
              value={inputValue}
              onValueChange={setInputValue}
              onSubmit={handleSendMessage}
              isLoading={isSending}
              className="max-w-3xl mx-auto"
            >
              <PromptInputTextarea
                placeholder="Ask a question about your documents..."
                disabled={isSending}
              />
              <PromptInputActions>
                <PromptInputAction tooltip="Upload PDF (Ctrl+U)">
                  <FileUploadTrigger asChild>
                    <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                      📎
                    </Button>
                  </FileUploadTrigger>
                </PromptInputAction>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf"
                  multiple
                  className="hidden"
                  onChange={(e) => {
                    if (e.target.files) {
                      handleFilesAdded(Array.from(e.target.files));
                    }
                  }}
                />
                <Button
                  type="submit"
                  size="sm"
                  disabled={!inputValue.trim() || isSending}
                >
                  {isSending ? <Loader variant="dots" size="sm" /> : 'Send'}
                </Button>
              </PromptInputActions>
            </PromptInput>
          </div>
        </FileUpload>
      </div>
    </div>
  );
}
