using HarmonyLib;
using System;
using System.Reflection;

namespace FunctionalGasStove
{
    public sealed class ModApi : IModApi
    {
        public void InitMod(Mod modInstance)
        {
            var harmony = new Harmony("Paffcio.FunctionalGasStove");
            harmony.PatchAll(Assembly.GetExecutingAssembly());
            Log.Out("[Functional Gas Stove] Harmony patches initialized.");
        }
    }

    /// <summary>
    /// Vanilla category tabs are selected by XUiC_CategoryList.SetupCategoriesByWorkstation.
    /// Vanilla knows the workstation key "campfire", but our dedicated stove window groups
    /// pass their own keys (cntgasRangeWhite/Grey/Black). We alias those keys to campfire
    /// just for category setup, so the stove gets the same category tabs as a campfire.
    /// </summary>
    [HarmonyPatch(typeof(XUiC_CategoryList), "SetupCategoriesByWorkstation")]
    public static class CategoryListWorkstationPatch
    {
        public static void Prefix(object[] __args)
        {
            if (__args == null || __args.Length == 0 || !(__args[0] is string workstation))
                return;

            switch (workstation.Trim().ToLowerInvariant())
            {
                case "cntgasrangewhite":
                case "cntgasrangegrey":
                case "cntgasrangeblack":
                    __args[0] = "campfire";
                    break;
            }
        }
    }
}
