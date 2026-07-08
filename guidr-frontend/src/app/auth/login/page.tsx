"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { postLogin } from "@/utils/api";
import { useAuth } from "@/contexts/AuthContext";
import { SignInPage, Testimonial } from "@/components/ui/sign-in";
import { useToast } from "@/contexts/ToastContext";

const sampleTestimonials: Testimonial[] = [
  {
    avatarSrc:
      "https://ui-avatars.com/api/?name=Sylvester&background=E8B4A0&color=1C2127&size=150&font-size=0.4&bold=true",
    name: "Sylvester",
    handle: "@geek_sly",
    text: "Guidr's recommendations pointed me to programs I'd never have found on my own. Genuinely saved me weeks of searching.",
  },
  {
    avatarSrc:
      "https://ui-avatars.com/api/?name=Derrick&background=4A7C74&color=ffffff&size=150&font-size=0.4&bold=true",
    name: "Derrick",
    handle: "@derrick",
    text: "The faculty matching and fit scores made it obvious which labs actually aligned with my research. Huge time-saver.",
  },
  {
    avatarSrc:
      "https://ui-avatars.com/api/?name=Nana+Kwame&background=1C2127&color=ffffff&size=150&font-size=0.4&bold=true",
    name: "Nana Kwame",
    handle: "@nkay",
    text: "Everything I needed in one place — schools, programs, and professors matched to my goals. This is how the search should feel.",
  },
];

export default function LoginPage() {
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const { login } = useAuth();
  const toast = useToast();

  async function handleSignIn(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setLoading(true);

    const formDataObj = new FormData(event.currentTarget);
    const email = formDataObj.get("email") as string;
    const password = formDataObj.get("password") as string;
    const rememberMe = formDataObj.get("rememberMe") === "on";

    try {
      const user = await postLogin({
        email,
        password,
        remember_me: rememberMe,
      });
      login(user);
      router.push("/dashboard");
    } catch (err: any) {
      const message =
        err?.message === "Failed to fetch"
          ? "We couldn't reach the server. Please check your connection and try again."
          : err?.message || "Invalid email or password";
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }

  function handleGoogleSignIn() {
    // TODO: Implement Google OAuth
    console.log("Google sign-in clicked");
  }

  function handleResetPassword() {
    router.push("/auth/reset-password");
  }

  function handleCreateAccount() {
    router.push("/auth/register");
  }

  return (
    <SignInPage
      title={
        <span className="font-light text-text tracking-tighter">
          Welcome Back
        </span>
      }
      description="Sign in to continue your graduate school journey"
      heroImageSrc="https://images.unsplash.com/photo-1627556704302-624286467c65?q=80&w=687&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D"
      testimonials={sampleTestimonials}
      onSignIn={handleSignIn}
      onGoogleSignIn={handleGoogleSignIn}
      onResetPassword={handleResetPassword}
      onCreateAccount={handleCreateAccount}
      error={error}
      loading={loading}
    />
  );
}
