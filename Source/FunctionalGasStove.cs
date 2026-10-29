using HarmonyLib;
using System;
using System.Collections.Generic;
using System.Reflection;

namespace FunctionalGasStove
{
    public sealed class ModApi : IModApi
    {
        public void InitMod(Mod modInstance)
        {
            var harmony = new Harmony("Paffcio.FunctionalGasStove");
            harmony.PatchAll(Assembly.GetExecutingAssembly());
            Log.Out("[Functional Gas Stove] Harmony patches initialized (V3.x fuel rules and recipe tabs).");
        }
    }

    internal static class StoveRules
    {
        internal const float GasCanBurnSeconds = 300f;

        internal static bool IsGasStove(TileEntityWorkstation station)
        {
            if (station == null || station.block == null)
                return false;

            string blockName = station.block.GetBlockName();
            return string.Equals(blockName, "cntgasRangeWhite", StringComparison.OrdinalIgnoreCase)
                || string.Equals(blockName, "cntgasRangeGrey", StringComparison.OrdinalIgnoreCase)
                || string.Equals(blockName, "cntgasRangeBlack", StringComparison.OrdinalIgnoreCase);
        }

        internal static bool IsGasCan(ItemStack stack)
        {
            if (stack == null || stack.IsEmpty() || stack.itemValue == null)
                return false;

            ItemClass itemClass = stack.itemValue.ItemClass;
            return itemClass != null && string.Equals(itemClass.GetItemName(), "ammoGasCan", StringComparison.OrdinalIgnoreCase);
        }
    }

    /// <summary>
    /// Apply a stove-specific fuel rule without changing ammoGasCan globally.
    /// Both methods exist in V3.3 and V3.4 and can be used by different fuel paths.
    /// Non-gas items may still appear in a fuel slot, but provide no burn time.
    /// </summary>
    [HarmonyPatch]
    public static class GasStoveFuelPatch
    {
        [HarmonyTargetMethods]
        public static IEnumerable<MethodBase> TargetMethods()
        {
            var stackArgs = new[] { typeof(ItemStack) };
            var internalFuel = AccessTools.Method(typeof(TileEntityWorkstation), "getFuelTime", stackArgs);
            var publicFuel = AccessTools.Method(typeof(TileEntityWorkstation), "GetFuelTime", stackArgs);

            if (internalFuel != null)
                yield return internalFuel;
            if (publicFuel != null)
                yield return publicFuel;
        }

        [HarmonyPostfix]
        public static void Postfix(TileEntityWorkstation __instance, ItemStack __0, ref float __result)
        {
            if (!StoveRules.IsGasStove(__instance))
                return;

            __result = StoveRules.IsGasCan(__0) ? StoveRules.GasCanBurnSeconds : 0f;
        }
    }

    /// <summary>
    /// Reuse vanilla campfire recipe categories for each gas stove window group.
    /// The original workstation key remains untouched outside this UI method.
    /// </summary>
    [HarmonyPatch(typeof(XUiC_CategoryList), "SetupCategoriesByWorkstation")]
    public static class CategoryListWorkstationPatch
    {
        [HarmonyPrefix]
        public static void Prefix(ref string __0)
        {
            if (__0 == null)
                return;

            switch (__0.Trim().ToLowerInvariant())
            {
                case "cntgasrangewhite":
                case "cntgasrangegrey":
                case "cntgasrangeblack":
                    __0 = "campfire";
                    break;
            }
        }
    }
}
