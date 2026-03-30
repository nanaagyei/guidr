'use client';

import { useState, useRef, useEffect } from 'react';
import { send2FACode } from '@/utils/api';

interface TwoFactorVerificationProps {
  email: string;
  /** Server accepts registration and password-reset flows only (no email code for login). */
  purpose: 'register' | 'password_reset';
  onVerified: (code: string) => void;
  onCancel?: () => void;
  error?: string;
}

export default function TwoFactorVerification({
  email,
  purpose,
  onVerified,
  onCancel,
  error: externalError,
}: TwoFactorVerificationProps) {
  const [code, setCode] = useState(['', '', '', '', '', '']);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [codeSent, setCodeSent] = useState(true); // Assume code is already sent by parent
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);
  const hasSentRef = useRef(false); // Prevent multiple sends

  useEffect(() => {
    // Focus first input when component mounts
    if (inputRefs.current[0]) {
      inputRefs.current[0].focus();
    }
  }, []);

  async function handleSendCode() {
    // Prevent multiple simultaneous sends
    if (sending || hasSentRef.current) {
      return;
    }
    
    setSending(true);
    setError('');
    hasSentRef.current = true;
    
    try {
      await send2FACode({ email, purpose });
      setCodeSent(true);
      // Reset the ref after a delay to allow resending
      setTimeout(() => {
        hasSentRef.current = false;
      }, 5000); // Wait 5 seconds before allowing another send
    } catch (err: any) {
      setError(err.message || 'Failed to send verification code');
      hasSentRef.current = false; // Reset on error
    } finally {
      setSending(false);
    }
  }

  function handleInputChange(index: number, value: string) {
    // Only allow digits
    if (value && !/^\d$/.test(value)) {
      return;
    }

    const newCode = [...code];
    newCode[index] = value;
    setCode(newCode);

    // Auto-focus next input
    if (value && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }

    // Auto-verify when all 6 digits are entered
    if (newCode.every(digit => digit !== '') && newCode.join('').length === 6) {
      handleVerify(newCode.join(''));
    }
  }

  function handleKeyDown(index: number, e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Backspace' && !code[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  }

  function handlePaste(e: React.ClipboardEvent<HTMLInputElement>) {
    e.preventDefault();
    const pastedData = e.clipboardData.getData('text').slice(0, 6);
    if (/^\d{6}$/.test(pastedData)) {
      const newCode = pastedData.split('');
      setCode(newCode);
      // Focus last input
      inputRefs.current[5]?.focus();
      // Auto-verify
      handleVerify(pastedData);
    }
  }

  async function handleVerify(verificationCode: string) {
    // Don't verify here - just pass the code to the parent
    // The login/register endpoint will verify it
    setLoading(true);
    setError('');
    try {
      // Just pass the code directly without verifying
      onVerified(verificationCode);
    } catch (err: any) {
      setError(err.message || 'Error processing code');
      // Clear code on error
      setCode(['', '', '', '', '', '']);
      inputRefs.current[0]?.focus();
    } finally {
      setLoading(false);
    }
  }

  const displayError = error || externalError;

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-xl font-semibold text-text mb-2">Verify Your Email</h3>
        <p className="text-gray-700/80 text-sm">
          We{"\u2019"}ve sent a 6-digit verification code to <strong>{email}</strong>
        </p>
      </div>

      {displayError && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-lg text-sm">
          {displayError}
        </div>
      )}

      {codeSent ? (
        <>
          <div className="flex gap-2 justify-center">
            {code.map((digit, index) => (
              <input
                key={index}
                ref={(el) => { inputRefs.current[index] = el; }}
                type="text"
                inputMode="numeric"
                maxLength={1}
                value={digit}
                onChange={(e) => handleInputChange(index, e.target.value)}
                onKeyDown={(e) => handleKeyDown(index, e)}
                onPaste={index === 0 ? handlePaste : undefined}
                disabled={loading}
                className="w-12 h-14 text-center text-2xl font-semibold border-2 border-border/30 rounded-lg focus:border-primary focus:outline-none bg-card/50 text-text disabled:opacity-50"
              />
            ))}
          </div>

          <div className="text-center">
            <button
              onClick={handleSendCode}
              disabled={sending}
              className="text-sm text-text hover:underline disabled:opacity-50"
            >
              {sending ? 'Sending...' : "Didn't receive a code? Resend"}
            </button>
          </div>
        </>
      ) : (
        <div className="text-center">
          <button
            onClick={handleSendCode}
            disabled={sending}
            className="px-4 py-2 bg-primary text-white font-semibold rounded-lg hover:bg-primaryHover transition disabled:opacity-50"
          >
            {sending ? 'Sending code...' : 'Send Verification Code'}
          </button>
        </div>
      )}

      {onCancel && (
        <div className="text-center">
          <button
            onClick={onCancel}
            className="text-sm text-gray-700/70 hover:text-text transition"
          >
            Cancel
          </button>
        </div>
      )}
    </div>
  );
}

