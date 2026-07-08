import type { Metadata } from 'next'
import '../styles/globals.css'
import { AuthProvider } from '@/contexts/AuthContext'
import { ProfileCompletionProvider } from '@/contexts/ProfileCompletionContext'
import { ToastProvider } from '@/contexts/ToastContext'
import ConditionalLayout from '@/components/ConditionalLayout'

export const metadata: Metadata = {
  title: 'Guidr – Graduate School Companion',
  description: 'Your guide to graduate school applications',
  icons: {
    icon: [
      { url: '/favicon-16x16.png', sizes: '16x16', type: 'image/png' },
      { url: '/favicon-32x32.png', sizes: '32x32', type: 'image/png' },
      { url: '/favicon.ico', sizes: 'any' },
    ],
    apple: [
      { url: '/apple-touch-icon.png', sizes: '180x180', type: 'image/png' },
    ],
  },
  manifest: '/site.webmanifest',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          <ProfileCompletionProvider>
            <ToastProvider>
              <ConditionalLayout>
                {children}
              </ConditionalLayout>
            </ToastProvider>
          </ProfileCompletionProvider>
        </AuthProvider>
      </body>
    </html>
  )
}
