import { defineAbility } from "@casl/ability";

export const defineUserAbility = (abilities = []) => {
  return defineAbility((can) => {
    abilities.forEach(({ action, subject, conditions }) => {
      if (conditions) {
        can(action, subject, conditions);
      } else {
        can(action, subject);
      }
    });
  });
};
