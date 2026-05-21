import { createApi } from '@reduxjs/toolkit/query/react'
import { createRuntimeBaseQuery } from '@/lib/api'
import config from '@/config'
import type { Issue, IssueComment } from '@/types'

interface IssueResponse {
  id: number
  title: string
  body: string | null
  state: string
  labels: string[]
  assignees: string[]
  created_at: string
  updated_at: string
  url: string | null
}

interface CommentResponse {
  id: number
  issue_id: number
  body: string
  author: string
  created_at: string
  updated_at: string
}

function toIssue(r: IssueResponse): Issue {
  return {
    id: r.id,
    title: r.title,
    body: r.body,
    state: r.state as 'open' | 'closed',
    labels: r.labels,
    assignees: r.assignees,
    createdAt: r.created_at,
    updatedAt: r.updated_at,
    url: r.url,
  }
}

function toComment(r: CommentResponse): IssueComment {
  return {
    id: r.id,
    issueId: r.issue_id,
    body: r.body,
    author: r.author,
    createdAt: r.created_at,
    updatedAt: r.updated_at,
  }
}

export const issuesApi = createApi({
  reducerPath: 'issuesApi',
  baseQuery: createRuntimeBaseQuery(config.runtimeUrl),
  tagTypes: ['Issue', 'IssueComment', 'IssueLabel'],
  endpoints: (builder) => ({
    listLabels: builder.query<string[], { workspaceId: string }>({
      query: ({ workspaceId }) => `/workspaces/${workspaceId}/issues/labels`,
      providesTags: ['IssueLabel'],
    }),
    listIssues: builder.query<Issue[], { workspaceId: string; state?: string; limit?: number }>({
      query: ({ workspaceId, state = 'open', limit }) => ({
        url: `/workspaces/${workspaceId}/issues`,
        params: { state, ...(limit != null ? { limit } : {}) },
      }),
      transformResponse: (response: IssueResponse[]) => response.map(toIssue),
      providesTags: ['Issue'],
    }),
    getIssue: builder.query<Issue, { workspaceId: string; issueId: number }>({
      query: ({ workspaceId, issueId }) => `/workspaces/${workspaceId}/issues/${issueId}`,
      transformResponse: (r: IssueResponse) => toIssue(r),
      providesTags: (_r, _e, { issueId }) => [{ type: 'Issue', id: issueId }],
    }),
    createIssue: builder.mutation<
      Issue,
      { workspaceId: string; body: { title: string; body?: string; labels?: string[]; assignees?: string[] } }
    >({
      query: ({ workspaceId, body }) => ({
        url: `/workspaces/${workspaceId}/issues`,
        method: 'POST',
        body,
      }),
      transformResponse: (r: IssueResponse) => toIssue(r),
      invalidatesTags: ['Issue', 'IssueLabel'],
    }),
    updateIssue: builder.mutation<
      Issue,
      {
        workspaceId: string
        issueId: number
        body: { title?: string; body?: string; state?: string; labels?: string[]; assignees?: string[] }
      }
    >({
      query: ({ workspaceId, issueId, body }) => ({
        url: `/workspaces/${workspaceId}/issues/${issueId}`,
        method: 'PATCH',
        body,
      }),
      transformResponse: (r: IssueResponse) => toIssue(r),
      invalidatesTags: (_r, _e, { issueId }) => [{ type: 'Issue', id: issueId }, 'Issue', 'IssueLabel'],
    }),
    deleteIssue: builder.mutation<void, { workspaceId: string; issueId: number }>({
      query: ({ workspaceId, issueId }) => ({
        url: `/workspaces/${workspaceId}/issues/${issueId}`,
        method: 'DELETE',
      }),
      invalidatesTags: ['Issue'],
    }),
    listComments: builder.query<IssueComment[], { workspaceId: string; issueId: number }>({
      query: ({ workspaceId, issueId }) => `/workspaces/${workspaceId}/issues/${issueId}/comments`,
      transformResponse: (response: CommentResponse[]) => response.map(toComment),
      providesTags: (_r, _e, { issueId }) => [{ type: 'IssueComment', id: issueId }],
    }),
    addComment: builder.mutation<IssueComment, { workspaceId: string; issueId: number; body: string }>({
      query: ({ workspaceId, issueId, body }) => ({
        url: `/workspaces/${workspaceId}/issues/${issueId}/comments`,
        method: 'POST',
        body: { body },
      }),
      transformResponse: (r: CommentResponse) => toComment(r),
      invalidatesTags: (_r, _e, { issueId }) => [{ type: 'IssueComment', id: issueId }],
    }),
    updateComment: builder.mutation<
      IssueComment,
      { workspaceId: string; issueId: number; commentId: number; body: string }
    >({
      query: ({ workspaceId, issueId, commentId, body }) => ({
        url: `/workspaces/${workspaceId}/issues/${issueId}/comments/${commentId}`,
        method: 'PATCH',
        body: { body },
      }),
      transformResponse: (r: CommentResponse) => toComment(r),
      invalidatesTags: (_r, _e, { issueId }) => [{ type: 'IssueComment', id: issueId }],
    }),
    deleteComment: builder.mutation<void, { workspaceId: string; issueId: number; commentId: number }>({
      query: ({ workspaceId, issueId, commentId }) => ({
        url: `/workspaces/${workspaceId}/issues/${issueId}/comments/${commentId}`,
        method: 'DELETE',
      }),
      invalidatesTags: (_r, _e, { issueId }) => [{ type: 'IssueComment', id: issueId }],
    }),
  }),
})

export const {
  useListLabelsQuery,
  useListIssuesQuery,
  useGetIssueQuery,
  useCreateIssueMutation,
  useUpdateIssueMutation,
  useDeleteIssueMutation,
  useListCommentsQuery,
  useAddCommentMutation,
  useUpdateCommentMutation,
  useDeleteCommentMutation,
} = issuesApi
