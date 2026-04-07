import { LoginForm } from '@/components/auth'

export default function Login() {
  return (
    <div className="flex min-h-svh flex-col items-center justify-center bg-muted p-6 md:p-10">
      <LoginForm className="w-full max-w-sm" />
    </div>
  )
}
