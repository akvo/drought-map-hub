"use server";

import { SignJWT, jwtVerify } from "jose";
import { cookies } from "next/headers";

/**
 * docs: https://nextjs.org/docs/app/building-your-application/authentication#1-generating-a-secret-key
 */
const secretKey = process.env.SESSION_SECRET;
const encodedKey = new TextEncoder().encode(secretKey);

export const encrypt = async ({ expirationTime, ...payload }) => {
  const expirationDate = new Date(expirationTime);
  const currentTime = new Date();
  const timeDifference = expirationDate - currentTime;

  // Convert to hours
  const hours = Math.floor(
    (timeDifference % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60)
  );
  return await new SignJWT(payload)
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime(`${hours} hours from now`)
    .sign(encodedKey);
};

export const decrypt = async (input) => {
  try {
    const { payload } = await jwtVerify(input, encodedKey, {
      algorithms: ["HS256"],
    });
    return payload;
  } catch {
    return {};
  }
};

export const signIn = async (formData) => {
  try {
    const req = await fetch(
      `${process.env.WEBDOMAIN}/api/v1/auth/login?format=json`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(formData),
      }
    );

    const { user, token, expiration_time: expirationTime } = await req.json();
    if (req.ok) {
      const expires = new Date(expirationTime);
      // Create the session
      const currentUser = await encrypt({
        id: user?.id,
        role: user?.role,
        abilities: user?.abilities,
        token,
        expirationTime,
      });

      // Save the session in a cookie
      cookies().set("currentUser", currentUser, { expires, httpOnly: true });
      return { message: "success", status: 200, role: user?.role };
    } else {
      return { message: "invalidLogin", status: 401 };
    }
  } catch {
    throw new Error("500");
  }
};

export const signOut = async () => {
  // Destroy the session
  cookies().set("currentUser", "", { expires: new Date(0) });
};

export const getSession = async () => {
  const session = cookies().get("currentUser")?.value;
  if (!session) return null;
  return await decrypt(session);
};
