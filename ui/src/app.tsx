import { useEffect } from 'react'
import './main.css'
import AppRoutes from '@/routes'
import { useAppDispatch } from '@/store/hooks'
import { restoreFromStorage } from '@/store/auth'

export default function App() {
  const dispatch = useAppDispatch()

  useEffect(() => {
    dispatch(restoreFromStorage())
  }, [dispatch])

  return <AppRoutes />
}
