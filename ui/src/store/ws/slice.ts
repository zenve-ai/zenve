import { createSlice } from '@reduxjs/toolkit'
import type { AppRootState } from '@/store/index'

export type WsStatus = 'idle' | 'connecting' | 'connected' | 'reconnecting' | 'failed'

interface WsState {
  status: WsStatus
}

const initialState: WsState = {
  status: 'idle',
}

export const wsSlice = createSlice({
  name: 'ws',
  initialState,
  reducers: {
    wsConnecting: (state) => { state.status = 'connecting' },
    wsConnected: (state) => { state.status = 'connected' },
    wsDisconnected: (state) => { state.status = 'idle' },
    wsReconnecting: (state) => { state.status = 'reconnecting' },
    wsFailed: (state) => { state.status = 'failed' },
  },
})

export const { wsConnecting, wsConnected, wsDisconnected, wsReconnecting, wsFailed } = wsSlice.actions

export const selectWsStatus = (state: AppRootState): WsStatus => state.ws.status

export default wsSlice.reducer
