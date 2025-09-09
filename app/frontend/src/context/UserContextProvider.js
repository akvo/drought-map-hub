"use client";

import { createContext, useContext, useReducer } from "react";

const UserContext = createContext(null);
const UserDispatchContext = createContext(null);
const initialValues = {
  id: null,
  email: null,
  role: null,
  email_verified: false,
  abilities: [],
};

const userReducer = (state, action) => {
  switch (action.type) {
    case "UPDATE":
      return {
        ...state,
        ...action.payload,
      };
    case "RESET":
      return initialValues;
    default:
      throw Error(
        `Unknown action: ${action.type}. Action type must be CAPITAL text.`
      );
  }
};

const UserContextProvider = ({ children, abilities = [] }) => {
  const [user, dispatch] = useReducer(userReducer, {
    ...initialValues,
    abilities,
  });

  return (
    <UserContext.Provider value={user}>
      <UserDispatchContext.Provider value={dispatch}>
        {children}
      </UserDispatchContext.Provider>
    </UserContext.Provider>
  );
};

export const useUserContext = () => useContext(UserContext);
export const useUserDispatch = () => useContext(UserDispatchContext);

export default UserContextProvider;
