"use client";

interface PasswordStrengthProps {
  password: string;
}

export function PasswordStrength({ password }: PasswordStrengthProps) {
  const hasMinLength = password.length >= 8;
  const hasUppercase = /[A-Z]/.test(password);
  const hasLowercase = /[a-z]/.test(password);
  const hasNumber = /[0-9]/.test(password);

  let points = 0;
  if (hasMinLength) points += 1;
  if (hasUppercase) points += 1;
  if (hasLowercase) points += 1;
  if (hasNumber) points += 1;

  let strength: "weak" | "fair" | "good" | "strong";
  let bgColor: string;
  let textColor: string;
  let fillPercent: number;

  if (!hasMinLength || points <= 1) {
    strength = "weak";
    bgColor = "bg-red-500";
    textColor = "text-red-600";
    fillPercent = 25;
  } else if (points === 2) {
    strength = "fair";
    bgColor = "bg-orange-500";
    textColor = "text-orange-600";
    fillPercent = 50;
  } else if (points === 3) {
    strength = "good";
    bgColor = "bg-yellow-500";
    textColor = "text-yellow-600";
    fillPercent = 75;
  } else {
    strength = "strong";
    bgColor = "bg-green-500";
    textColor = "text-green-600";
    fillPercent = 100;
  }

  const strengthLabel =
    strength.charAt(0).toUpperCase() + strength.slice(1);

  return (
    <div className="space-y-2">
      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${bgColor} transition-all duration-200`}
          style={{ width: `${fillPercent}%` }}
        />
      </div>

      <p className={`text-sm font-medium ${textColor}`}>
        Strength: {strengthLabel}
      </p>

      <ul className="text-sm space-y-1 text-gray-700">
        <li className={hasMinLength ? "text-green-600" : "text-gray-400"}>
          {hasMinLength ? "✓" : "✗"} At least 8 characters
        </li>
        <li className={hasUppercase ? "text-green-600" : "text-gray-400"}>
          {hasUppercase ? "✓" : "✗"} Contains uppercase letter
        </li>
        <li className={hasLowercase ? "text-green-600" : "text-gray-400"}>
          {hasLowercase ? "✓" : "✗"} Contains lowercase letter
        </li>
        <li className={hasNumber ? "text-green-600" : "text-gray-400"}>
          {hasNumber ? "✓" : "✗"} Contains number
        </li>
      </ul>
    </div>
  );
}
