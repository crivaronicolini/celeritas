import { useCallback, useEffect, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Loader } from '@/components/ui/loader';
import {
  getAnalytics,
  getRecentInteractions,
  getUnusedDocuments,
  getUnansweredPatterns,
  type Analytics,
  type Interaction,
  type Document,
  type UnansweredPatterns,
} from '@/lib/api';

export function AnalyticsPage() {
  const { user, loading: authLoading } = useAuth();
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [recentInteractions, setRecentInteractions] = useState<Interaction[]>([]);
  const [unusedDocuments, setUnusedDocuments] = useState<Document[]>([]);
  const [unansweredPatterns, setUnansweredPatterns] = useState<UnansweredPatterns | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadAnalytics = useCallback(async () => {
    try {
      const [analyticsData, interactions, unused, patterns] = await Promise.all([
        getAnalytics(),
        getRecentInteractions(10),
        getUnusedDocuments(),
        getUnansweredPatterns(),
      ]);
      setAnalytics(analyticsData);
      setRecentInteractions(interactions);
      setUnusedDocuments(unused);
      setUnansweredPatterns(patterns);
    } catch (err) {
      console.error('Failed to load analytics:', err);
      setError('Failed to load analytics. You may not have permission to view this page.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (user?.is_superuser) {
      loadAnalytics();
    } else if (!authLoading) {
      setIsLoading(false);
    }
  }, [user, authLoading, loadAnalytics]);

  if (authLoading || isLoading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-3.5rem)]">
        <Loader variant="dots" size="lg" />
      </div>
    );
  }

  if (!user) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-3.5rem)]">
        <p className="text-muted-foreground">Sign in to view analytics</p>
      </div>
    );
  }

  if (!user.is_superuser) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-3.5rem)]">
        <p className="text-muted-foreground">You don't have permission to view this page</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-3.5rem)]">
        <p className="text-destructive">{error}</p>
      </div>
    );
  }

  if (!analytics) return null;

  const feedbackPercentage = analytics.feedback_statistics.positive_feedback_percentage;

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      <h1 className="text-2xl font-semibold mb-6">Analytics Dashboard</h1>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Total Interactions</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{analytics.total_interactions}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Avg Response Time</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{analytics.average_response_time_seconds.toFixed(2)}s</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Total Feedback</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{analytics.feedback_statistics.total_feedback_count}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Positive Feedback</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{feedbackPercentage.toFixed(0)}%</p>
            <div className="mt-2 h-2 bg-muted rounded-full overflow-hidden">
              <div
                className="h-full bg-green-500 rounded-full"
                style={{ width: `${feedbackPercentage}%` }}
              />
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Most Queried Documents */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Most Queried Documents</CardTitle>
          </CardHeader>
          <CardContent>
            {analytics.most_frequently_queried_documents.length === 0 ? (
              <p className="text-muted-foreground text-sm">No data yet</p>
            ) : (
              <div className="space-y-3">
                {analytics.most_frequently_queried_documents.slice(0, 5).map((doc, idx) => (
                  <div key={idx} className="flex items-center justify-between">
                    <span className="text-sm truncate flex-1 mr-4">{doc.filename}</span>
                    <span className="text-sm font-medium">{doc.query_count} queries</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Most Asked Questions */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Most Asked Questions</CardTitle>
          </CardHeader>
          <CardContent>
            {analytics.most_often_asked_questions.length === 0 ? (
              <p className="text-muted-foreground text-sm">No data yet</p>
            ) : (
              <div className="space-y-3">
                {analytics.most_often_asked_questions.slice(0, 5).map((q, idx) => (
                  <div key={idx} className="flex items-center justify-between">
                    <span className="text-sm truncate flex-1 mr-4">{q.question}</span>
                    <span className="text-sm font-medium">{q.ask_count}x</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Interactions */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Recent Interactions</CardTitle>
          </CardHeader>
          <CardContent>
            {recentInteractions.length === 0 ? (
              <p className="text-muted-foreground text-sm">No interactions yet</p>
            ) : (
              <div className="space-y-4">
                {recentInteractions.slice(0, 5).map((interaction) => (
                  <div key={interaction.id} className="border-b border-border pb-3 last:border-0">
                    <p className="text-sm font-medium truncate">{interaction.question}</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {new Date(interaction.timestamp).toLocaleString()} ({interaction.response_time.toFixed(2)}s)
                    </p>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Unused Documents */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Unused Documents</CardTitle>
          </CardHeader>
          <CardContent>
            {unusedDocuments.length === 0 ? (
              <p className="text-muted-foreground text-sm">All documents have been used</p>
            ) : (
              <div className="space-y-2">
                {unusedDocuments.slice(0, 5).map((doc) => (
                  <div key={doc.id} className="flex items-center gap-2">
                    <span className="text-xl">📄</span>
                    <span className="text-sm truncate">{doc.filename}</span>
                  </div>
                ))}
                {unusedDocuments.length > 5 && (
                  <p className="text-xs text-muted-foreground">
                    +{unusedDocuments.length - 5} more
                  </p>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Unanswered Patterns */}
      {unansweredPatterns && (
        <div className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Questions Needing Attention</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div>
                  <h4 className="text-sm font-medium mb-3">Without Document Sources</h4>
                  {unansweredPatterns.questions_without_documents.length === 0 ? (
                    <p className="text-muted-foreground text-sm">None</p>
                  ) : (
                    <div className="space-y-2">
                      {unansweredPatterns.questions_without_documents.slice(0, 3).map((q) => (
                        <p key={q.id} className="text-sm truncate">{q.question}</p>
                      ))}
                    </div>
                  )}
                </div>
                <div>
                  <h4 className="text-sm font-medium mb-3">With Negative Feedback</h4>
                  {unansweredPatterns.questions_with_negative_feedback.length === 0 ? (
                    <p className="text-muted-foreground text-sm">None</p>
                  ) : (
                    <div className="space-y-2">
                      {unansweredPatterns.questions_with_negative_feedback.slice(0, 3).map((q) => (
                        <p key={q.id} className="text-sm truncate">{q.question}</p>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
