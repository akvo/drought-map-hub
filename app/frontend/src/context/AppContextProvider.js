"use client";

import { createContext, useContext, useReducer } from "react";

const AppContext = createContext(null);
const AppDispatchContext = createContext(null);
const initialValues = {
  administrations: [],
  geoData: null,
  activeAdm: null,
  selectedAdms: [],
  isBulkAction: false,
  refreshMap: false,
};

const appReducer = (state, action) => {
  switch (action.type) {
    case "REFRESH_MAP_FALSE":
      return {
        ...state,
        refreshMap: false,
      };
    case "REFRESH_MAP_TRUE":
      return {
        ...state,
        refreshMap: true,
      };
    case "REMOVE_ACTIVE_ADM":
      return {
        ...state,
        activeAdm: null,
      };
    case "UPDATE_ACTIVE_ADM":
      return {
        ...state,
        activeAdm: {
          ...state.activeAdm,
          ...action.payload,
        },
      };
    case "SET_ACTIVE_ADM":
      return {
        ...state,
        activeAdm: action.payload,
      };
    case "SET_SELECTED_ADM":
      return {
        ...state,
        selectedAdms: action.payload,
      };
    case "RESET_SELECTED_ADM":
      return {
        ...state,
        selectedAdms: [],
      };
    case "REMOVE_SELECTED_ADM":
      return {
        ...state,
        selectedAdms: state.selectedAdms.filter((s) => s !== action.payload),
      };
    case "ADD_SELECTED_ADM":
      return {
        ...state,
        selectedAdms: [...state.selectedAdms, action.payload],
      };
    case "SET_IS_BULK_ACTION":
      return {
        ...state,
        isBulkAction: action.payload,
      };
    case "SET_ADM":
      return {
        ...state,
        administrations: action.payload,
      };
    case "SET_GEODATA":
      return {
        ...state,
        geoData: action.payload,
      };
    default:
      throw Error(
        `Unknown action: ${action.type}. Action type must be CAPITAL text.`
      );
  }
};

const AppContextProvider = ({ children }) => {
  const [value, dispatch] = useReducer(appReducer, initialValues);

  return (
    <AppContext.Provider value={value}>
      <AppDispatchContext.Provider value={dispatch}>
        {children}
      </AppDispatchContext.Provider>
    </AppContext.Provider>
  );
};

export const useAppContext = () => useContext(AppContext);
export const useAppDispatch = () => useContext(AppDispatchContext);

export default AppContextProvider;
