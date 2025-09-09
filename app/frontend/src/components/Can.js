"use client";

import { useUserContext } from "@/context/UserContextProvider";
import { defineUserAbility } from "@/lib";

const Can = ({ I, children, a = null, an = null }) => {
  const subject = a || an;
  const userContext = useUserContext();
  const userAbilities = userContext?.abilities || [];
  const ability = defineUserAbility(userAbilities);
  return ability.can(I, subject, "owner") ? children : null;
};

export default Can;
