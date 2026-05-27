import { SignupForm } from '@/components/auth'

export default function Signup() {
  return (
    <div className="flex min-h-svh flex-col items-center justify-center bg-muted p-6 md:p-10">
      <SignupForm className="w-full max-w-sm" />
    </div>
  )
}
