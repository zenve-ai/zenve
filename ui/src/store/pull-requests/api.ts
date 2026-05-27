import { createApi } from '@reduxjs/toolkit/query/react'
import { createRuntimeBaseQuery } from '@/lib/api'
import config from '@/config'
import type { PRComment, PullRequest } from '@/types'

interface PRCommentResponse {
  author: string
  body: string
  created_at: string
}

interface PRResponse {
  number: number
  title: string
  body: string | null
  state: string
  labels: string[]
  assignees: string[]
  head: string
  base: string
  draft: boolean
  created_at: string
  url: string | null
  comments: PRCommentResponse[]
}

function toPRComment(r: PRCommentResponse): PRComment {
  return {
    author: r.author,
    body: r.body,
    createdAt: r.created_at,
  }
}

function toPullRequest(r: PRResponse): PullRequest {
  return {
    number: r.number,
    title: r.title,
    body: r.body,
    state: r.state as 'open' | 'closed',
    labels: r.labels,
    assignees: r.assignees,
    head: r.head,
    base: r.base,
    draft: r.draft,
    createdAt: r.created_at,
    url: r.url,
    comments: r.comments.map(toPRComment),
  }
}

export const pullRequestsApi = createApi({
  reducerPath: 'pullRequestsApi',
  baseQuery: createRuntimeBaseQuery(config.runtimeUrl),
  tagTypes: ['PullRequest'],
  endpoints: (builder) => ({
    listPullRequests: builder.query<PullRequest[], { workspaceId: string; state?: string; limit?: number }>({
      query: ({ workspaceId, state = 'open', limit }) => ({
        url: `/workspaces/${workspaceId}/pull-requests`,
        params: { state, ...(limit != null ? { limit } : {}) },
      }),
      transformResponse: (response: PRResponse[]) => response.map(toPullRequest),
      providesTags: ['PullRequest'],
    }),
    getPullRequest: builder.query<PullRequest, { workspaceId: string; prNumber: number }>({
      query: ({ workspaceId, prNumber }) => `/workspaces/${workspaceId}/pull-requests/${prNumber}`,
      transformResponse: (r: PRResponse) => toPullRequest(r),
      providesTags: (_r, _e, { prNumber }) => [{ type: 'PullRequest', id: prNumber }],
    }),
  }),
})

export const { useListPullRequestsQuery, useGetPullRequestQuery } = pullRequestsApi
