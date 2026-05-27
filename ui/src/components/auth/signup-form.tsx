import { useState } from "react"
import { useNavigate } from "react-router"
import { cn } from "@/lib/utils"
import { useSignupMutation } from "@/store/auth"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field"
import { Input } from "@/components/ui/input"

export function SignupForm({
  className,
  ...props
}: React.ComponentProps<"div">) {
  const [email, setEmail] = useState("")
  const [name, setName] = useState("")
  const [password, setPassword] = useState("")
  const [signup, { isLoading, isError, error }] = useSignupMutation()
  const navigate = useNavigate()

  const errorMessage =
    isError && (error as { data?: { detail?: string } })?.data?.detail
      ? (error as { data: { detail: string } }).data.detail
      : isError
        ? "Could not create account. Try a different email."
        : null

  return (
    <div className={cn("flex flex-col gap-6", className)} {...props}>
      <Card>
        <CardHeader className="text-center">
          <CardTitle className="text-xl">Create an account</CardTitle>
          <CardDescription>
            Enter your details to get started
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={(e) => { e.preventDefault(); signup({ email, name: name || undefined, password }) }}>
            <FieldGroup>
              <Field>
                <FieldLabel htmlFor="name">Name</FieldLabel>
                <Input
                  id="name"
                  type="text"
                  placeholder="Your name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </Field>
              <Field>
                <FieldLabel htmlFor="email">Email</FieldLabel>
                <Input
                  id="email"
                  type="email"
                  placeholder="m@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </Field>
              <Field>
                <FieldLabel htmlFor="password">Password</FieldLabel>
                <Input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </Field>
              <Field>
                {errorMessage && <p className="text-sm text-destructive">{errorMessage}</p>}
                <Button type="submit" disabled={isLoading}>
                  {isLoading ? "Creating account..." : "Sign up"}
                </Button>
                <FieldDescription className="text-center">
                  Already have an account?{" "}
                  <button
                    type="button"
                    className="underline-offset-4 hover:underline"
                    onClick={() => navigate("/login")}
                  >
                    Log in
                  </button>
                </FieldDescription>
              </Field>
            </FieldGroup>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
