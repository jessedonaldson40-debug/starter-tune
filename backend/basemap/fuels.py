"""
StandAIlone BaseMap Constructor
===============================

Fuel Chemistry Engine for the BaseMap Constructor kernel.

This module describes fuel and nothing else.

It owns:
- canonical fuel-property profiles,
- gasoline / ethanol blend resolution,
- stoichiometric air-fuel ratio,
- lambda / AFR conversion,
- liquid-fuel density correction,
- lower-heating-value and volumetric-energy calculation,
- oxygen-content representation,
- latent-heat and charge-cooling indicators,
- cold-start difficulty indicators,
- knock-resistance evidence representation,
- chemistry-only lambda guidance,
- fuel-property assumptions, provenance, and findings.

It does not own:
- injector pulse width,
- injector duty cycle,
- airflow or volumetric efficiency,
- ignition timing,
- boost control,
- combustion prediction,
- calibration authority.

Fuel doctrine
-------------
- Lambda is the canonical mixture-strength quantity.
- AFR is a fuel-specific human-readable translation of lambda.
- Product labels such as "E85" are not treated as measured composition.
- User or measured properties override reference profiles only when explicit.
- Unknown chemistry remains unknown; the module does not manufacture certainty.
- Fuel-property guidance is not a complete calibration recommendation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable

from .models import (
    BaseMapConfiguration,
    EngineeringFinding,
    EngineeringValue,
    EvidenceQuality,
    EvidenceSource,
    FindingDisposition,
    FindingSeverity,
    FuelSpecification,
    FuelType,
    OperatingRegion,
)


FUEL_ENGINE_VERSION = "fuels/1.0"
REFERENCE_TEMPERATURE_C = 15.0

# Linear volumetric-expansion approximation used only when a measured product-
# specific coefficient is unavailable. Hydrocarbon and alcohol blends vary.
DEFAULT_DENSITY_THERMAL_EXPANSION_PER_C = 0.00095


class FuelChemistryError(ValueError):
    """Raised when a fuel-chemistry calculation cannot be performed safely."""


@dataclass(frozen=True, slots=True)
class FuelProfile:
    """Reference chemistry profile, not a product guarantee."""

    profile_id: str
    fuel_type: FuelType
    display_name: str

    stoichiometric_afr: float
    density_kg_per_l_at_15c: float
    lower_heating_value_mj_per_kg: float
    latent_heat_kj_per_kg: float
    oxygen_mass_fraction: float

    research_octane_number: float | None
    motor_octane_number: float | None

    charge_cooling_index: float
    cold_start_difficulty_index: float
    combustion_stability_index: float

    typical_ethanol_pct: float | None = None
    density_expansion_per_c: float = DEFAULT_DENSITY_THERMAL_EXPANSION_PER_C
    assumptions: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class LambdaGuidance:
    """Chemistry-only lambda guidance for one operating intent."""

    operating_region: OperatingRegion
    minimum_lambda: float
    nominal_lambda: float
    maximum_lambda: float
    rationale: str
    validation_required: bool = True


@dataclass(slots=True)
class FuelState:
    """Canonical fuel state consumed by downstream engineering disciplines."""

    fuel_type: FuelType
    profile_id: str | None
    display_name: str

    stoichiometric_afr: float | None
    density_kg_per_l: float | None
    density_reference_temperature_c: float | None
    fuel_temperature_c: float | None

    lower_heating_value_mj_per_kg: float | None
    volumetric_energy_mj_per_l: float | None
    latent_heat_kj_per_kg: float | None
    oxygen_mass_fraction: float | None

    research_octane_number: float | None
    motor_octane_number: float | None
    anti_knock_index: float | None

    ethanol_content_pct: float | None

    charge_cooling_index: float | None
    cold_start_difficulty_index: float | None
    combustion_stability_index: float | None

    lambda_guidance: list[LambdaGuidance] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    findings: list[EngineeringFinding] = field(default_factory=list)

    fuel_version: str = FUEL_ENGINE_VERSION

    @property
    def is_characterized(self) -> bool:
        return (
            self.stoichiometric_afr is not None
            and self.density_kg_per_l is not None
            and self.lower_heating_value_mj_per_kg is not None
        )

    @property
    def has_blocking_findings(self) -> bool:
        return any(finding.blocking for finding in self.findings)


REFERENCE_PROFILES: dict[str, FuelProfile] = {
    "gasoline_reference": FuelProfile(
        profile_id="gasoline_reference",
        fuel_type=FuelType.GASOLINE,
        display_name="Reference gasoline",
        stoichiometric_afr=14.68,
        density_kg_per_l_at_15c=0.745,
        lower_heating_value_mj_per_kg=43.0,
        latent_heat_kj_per_kg=350.0,
        oxygen_mass_fraction=0.0,
        research_octane_number=None,
        motor_octane_number=None,
        charge_cooling_index=0.35,
        cold_start_difficulty_index=0.15,
        combustion_stability_index=0.90,
        assumptions=(
            "Generic gasoline chemistry is used because no product-specific fuel profile was supplied.",
            "Octane is intentionally unresolved because gasoline grade and formulation are unknown.",
        ),
    ),
    "e85_reference": FuelProfile(
        profile_id="e85_reference",
        fuel_type=FuelType.E85,
        display_name="Reference E85 blend",
        stoichiometric_afr=9.85,
        density_kg_per_l_at_15c=0.785,
        lower_heating_value_mj_per_kg=29.2,
        latent_heat_kj_per_kg=760.0,
        oxygen_mass_fraction=0.296,
        research_octane_number=None,
        motor_octane_number=None,
        charge_cooling_index=0.82,
        cold_start_difficulty_index=0.68,
        combustion_stability_index=0.88,
        typical_ethanol_pct=85.0,
        assumptions=(
            "The E85 label is treated as a nominal reference blend, not measured ethanol content.",
            "Seasonal and regional E85 composition can differ materially from the nominal profile.",
            "Octane is not synthesized from ethanol percentage alone.",
        ),
    ),
    "ethanol_reference": FuelProfile(
        profile_id="ethanol_reference",
        fuel_type=FuelType.ETHANOL,
        display_name="Reference anhydrous ethanol",
        stoichiometric_afr=9.00,
        density_kg_per_l_at_15c=0.794,
        lower_heating_value_mj_per_kg=26.8,
        latent_heat_kj_per_kg=840.0,
        oxygen_mass_fraction=0.347,
        research_octane_number=None,
        motor_octane_number=None,
        charge_cooling_index=0.90,
        cold_start_difficulty_index=0.82,
        combustion_stability_index=0.84,
        typical_ethanol_pct=100.0,
        assumptions=(
            "Reference anhydrous ethanol properties are used.",
            "Water content and denaturant chemistry are not represented.",
        ),
    ),
    "methanol_reference": FuelProfile(
        profile_id="methanol_reference",
        fuel_type=FuelType.METHANOL,
        display_name="Reference methanol",
        stoichiometric_afr=6.47,
        density_kg_per_l_at_15c=0.792,
        lower_heating_value_mj_per_kg=19.9,
        latent_heat_kj_per_kg=1100.0,
        oxygen_mass_fraction=0.499,
        research_octane_number=None,
        motor_octane_number=None,
        charge_cooling_index=1.00,
        cold_start_difficulty_index=0.95,
        combustion_stability_index=0.78,
        assumptions=(
            "Reference neat methanol properties are used.",
            "Water absorption and lubricant-additive effects are not represented.",
        ),
    ),
}


class _FuelFindingCollector:
    def __init__(self) -> None:
        self._findings: list[EngineeringFinding] = []
        self._keys: set[tuple[str, tuple[str, ...]]] = set()
        self._sequence = 0

    @property
    def findings(self) -> list[EngineeringFinding]:
        return list(self._findings)

    def add(
        self,
        *,
        code: str,
        title: str,
        message: str,
        severity: FindingSeverity,
        affected_fields: Iterable[str] = (),
        operating_regions: Iterable[OperatingRegion] = (),
        evidence_ids: Iterable[str] = (),
        recommendation: str | None = None,
        blocking: bool = False,
        metadata: dict[str, object] | None = None,
    ) -> None:
        fields = tuple(affected_fields)
        key = (code, fields)
        if key in self._keys:
            return

        self._keys.add(key)
        self._sequence += 1
        self._findings.append(
            EngineeringFinding(
                finding_id=f"FUEL-{self._sequence:04d}-{code}",
                code=code,
                title=title,
                message=message,
                severity=severity,
                disposition=FindingDisposition.STRENGTHEN,
                subsystem="fuel_chemistry",
                operating_regions=list(operating_regions),
                evidence_ids=list(evidence_ids),
                affected_fields=list(fields),
                recommendation=recommendation,
                constitutional_basis=(
                    "Fuel properties must be explicit, evidence-backed, and separated "
                    "from injector, airflow, ignition, and calibration assumptions."
                ),
                blocking=blocking,
                metadata=metadata or {},
            )
        )


def _finite(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _engineering_value_number(value: EngineeringValue[float]) -> float | None:
    if value.value is None or not _finite(value.value):
        return None
    return float(value.value)


def lambda_to_afr(lambda_value: float, stoichiometric_afr: float) -> float:
    """Translate lambda into fuel-specific AFR."""
    if not _finite(lambda_value) or float(lambda_value) <= 0.0:
        raise FuelChemistryError("Lambda must be finite and greater than zero.")
    if not _finite(stoichiometric_afr) or float(stoichiometric_afr) <= 0.0:
        raise FuelChemistryError("Stoichiometric AFR must be finite and greater than zero.")
    return float(lambda_value) * float(stoichiometric_afr)


def afr_to_lambda(afr: float, stoichiometric_afr: float) -> float:
    """Translate fuel-specific AFR into canonical lambda."""
    if not _finite(afr) or float(afr) <= 0.0:
        raise FuelChemistryError("AFR must be finite and greater than zero.")
    if not _finite(stoichiometric_afr) or float(stoichiometric_afr) <= 0.0:
        raise FuelChemistryError("Stoichiometric AFR must be finite and greater than zero.")
    return float(afr) / float(stoichiometric_afr)


def density_at_temperature(
    density_kg_per_l_at_reference: float,
    fuel_temperature_c: float,
    *,
    reference_temperature_c: float = REFERENCE_TEMPERATURE_C,
    expansion_per_c: float = DEFAULT_DENSITY_THERMAL_EXPANSION_PER_C,
) -> float:
    """
    Approximate liquid-fuel density at temperature.

    The relationship is intentionally simple and must be replaced by a
    product-specific density curve when one is available.
    """
    values = (
        density_kg_per_l_at_reference,
        fuel_temperature_c,
        reference_temperature_c,
        expansion_per_c,
    )
    if not all(_finite(value) for value in values):
        raise FuelChemistryError("Density correction inputs must be finite.")
    if density_kg_per_l_at_reference <= 0.0:
        raise FuelChemistryError("Reference density must be greater than zero.")
    if expansion_per_c < 0.0:
        raise FuelChemistryError("Thermal expansion coefficient cannot be negative.")

    delta_c = fuel_temperature_c - reference_temperature_c
    denominator = 1.0 + expansion_per_c * delta_c
    if denominator <= 0.0:
        raise FuelChemistryError("Temperature correction produced an invalid density denominator.")

    return density_kg_per_l_at_reference / denominator


def volumetric_energy_density(
    lower_heating_value_mj_per_kg: float,
    density_kg_per_l: float,
) -> float:
    """Calculate lower-heating-value energy density in MJ/L."""
    if not _finite(lower_heating_value_mj_per_kg) or lower_heating_value_mj_per_kg <= 0.0:
        raise FuelChemistryError("Lower heating value must be finite and greater than zero.")
    if not _finite(density_kg_per_l) or density_kg_per_l <= 0.0:
        raise FuelChemistryError("Fuel density must be finite and greater than zero.")
    return lower_heating_value_mj_per_kg * density_kg_per_l


def anti_knock_index(ron: float | None, mon: float | None) -> float | None:
    """Return (RON + MON) / 2 when both values are explicitly available."""
    if ron is None or mon is None:
        return None
    if not _finite(ron) or not _finite(mon):
        raise FuelChemistryError("RON and MON must be finite when supplied.")
    return (float(ron) + float(mon)) / 2.0


def _mass_fraction_from_volume_fraction(
    volume_fraction: float,
    component_density: float,
    carrier_density: float,
) -> float:
    component_mass = volume_fraction * component_density
    carrier_mass = (1.0 - volume_fraction) * carrier_density
    total_mass = component_mass + carrier_mass
    if total_mass <= 0.0:
        raise FuelChemistryError("Blend mass must be greater than zero.")
    return component_mass / total_mass


def blend_gasoline_ethanol_profile(ethanol_pct: float) -> FuelProfile:
    """
    Construct a transparent gasoline/ethanol reference blend.

    Density is blended volumetrically. Stoichiometric AFR and lower heating
    value are blended on a mass basis. Octane is deliberately left unresolved
    because blending response is product-specific and not reliably linear.
    """
    if not _finite(ethanol_pct) or not 0.0 <= float(ethanol_pct) <= 100.0:
        raise FuelChemistryError("Ethanol content must be between 0 and 100 percent.")

    ethanol_fraction_v = float(ethanol_pct) / 100.0
    gasoline = REFERENCE_PROFILES["gasoline_reference"]
    ethanol = REFERENCE_PROFILES["ethanol_reference"]

    density = (
        ethanol_fraction_v * ethanol.density_kg_per_l_at_15c
        + (1.0 - ethanol_fraction_v) * gasoline.density_kg_per_l_at_15c
    )
    ethanol_fraction_m = _mass_fraction_from_volume_fraction(
        ethanol_fraction_v,
        ethanol.density_kg_per_l_at_15c,
        gasoline.density_kg_per_l_at_15c,
    )
    gasoline_fraction_m = 1.0 - ethanol_fraction_m

    # Stoichiometric fuel/air ratios add on a fuel-mass basis. Convert each
    # component AFR to fuel/air, blend, then invert back to AFR.
    fuel_air_stoich = (
        gasoline_fraction_m / gasoline.stoichiometric_afr
        + ethanol_fraction_m / ethanol.stoichiometric_afr
    )
    stoich = 1.0 / fuel_air_stoich

    lhv = (
        gasoline_fraction_m * gasoline.lower_heating_value_mj_per_kg
        + ethanol_fraction_m * ethanol.lower_heating_value_mj_per_kg
    )
    latent_heat = (
        gasoline_fraction_m * gasoline.latent_heat_kj_per_kg
        + ethanol_fraction_m * ethanol.latent_heat_kj_per_kg
    )
    oxygen_fraction = ethanol_fraction_m * ethanol.oxygen_mass_fraction

    charge_cooling = (
        gasoline_fraction_m * gasoline.charge_cooling_index
        + ethanol_fraction_m * ethanol.charge_cooling_index
    )
    cold_start = (
        gasoline_fraction_m * gasoline.cold_start_difficulty_index
        + ethanol_fraction_m * ethanol.cold_start_difficulty_index
    )
    stability = (
        gasoline_fraction_m * gasoline.combustion_stability_index
        + ethanol_fraction_m * ethanol.combustion_stability_index
    )

    return FuelProfile(
        profile_id=f"gasoline_ethanol_e{ethanol_pct:.1f}",
        fuel_type=FuelType.FLEX_FUEL,
        display_name=f"Reference gasoline/ethanol blend E{ethanol_pct:.1f}",
        stoichiometric_afr=stoich,
        density_kg_per_l_at_15c=density,
        lower_heating_value_mj_per_kg=lhv,
        latent_heat_kj_per_kg=latent_heat,
        oxygen_mass_fraction=oxygen_fraction,
        research_octane_number=None,
        motor_octane_number=None,
        charge_cooling_index=charge_cooling,
        cold_start_difficulty_index=cold_start,
        combustion_stability_index=stability,
        typical_ethanol_pct=float(ethanol_pct),
        assumptions=(
            "Reference gasoline and ethanol properties were blended from stated ethanol volume fraction.",
            "Blend chemistry is an engineering approximation, not a substitute for a measured fuel certificate.",
            "Octane was not interpolated from ethanol percentage.",
        ),
    )


def _reference_profile_for_specification(
    specification: FuelSpecification,
    collector: _FuelFindingCollector,
) -> FuelProfile | None:
    fuel_type = specification.fuel_type
    ethanol_pct = _engineering_value_number(specification.ethanol_content_pct)

    if fuel_type is FuelType.FLEX_FUEL:
        if ethanol_pct is None:
            collector.add(
                code="FLEX_ETHANOL_CONTENT_UNKNOWN",
                title="Flex-fuel composition is unknown",
                message=(
                    "A flex-fuel label does not define current ethanol content. "
                    "Fuel chemistry cannot be fully resolved without measured or declared composition."
                ),
                severity=FindingSeverity.BLOCKING,
                affected_fields=("fuel_system.fuel.ethanol_content_pct",),
                operating_regions=(
                    OperatingRegion.STARTUP,
                    OperatingRegion.COLD_OPERATION,
                    OperatingRegion.HIGH_LOAD,
                    OperatingRegion.FULL_LOAD,
                ),
                recommendation="Supply measured ethanol content from a characterized sensor or fuel test.",
                blocking=True,
            )
            return None
        return blend_gasoline_ethanol_profile(ethanol_pct)

    if fuel_type is FuelType.E85:
        if ethanol_pct is not None:
            return blend_gasoline_ethanol_profile(ethanol_pct)
        collector.add(
            code="E85_CONTENT_ASSUMED",
            title="Nominal E85 composition assumed",
            message=(
                "The E85 product label was used without measured ethanol content. "
                "Seasonal blend variation can materially change stoichiometry and fuel demand."
            ),
            severity=FindingSeverity.WARNING,
            affected_fields=("fuel_system.fuel.ethanol_content_pct",),
            operating_regions=(OperatingRegion.COLD_OPERATION, OperatingRegion.FULL_LOAD),
            recommendation="Measure ethanol content before granting high-load fuel authority.",
        )
        return REFERENCE_PROFILES["e85_reference"]

    if fuel_type is FuelType.GASOLINE:
        return REFERENCE_PROFILES["gasoline_reference"]

    if fuel_type is FuelType.ETHANOL:
        return REFERENCE_PROFILES["ethanol_reference"]

    if fuel_type is FuelType.METHANOL:
        return REFERENCE_PROFILES["methanol_reference"]

    if fuel_type is FuelType.RACE_GASOLINE:
        collector.add(
            code="RACE_FUEL_PRODUCT_REQUIRED",
            title="Race-fuel product is not characterized",
            message=(
                "Race gasoline is not one chemistry. Product-specific stoichiometry, density, "
                "heating value, and octane evidence are required."
            ),
            severity=FindingSeverity.BLOCKING,
            affected_fields=("fuel_system.fuel",),
            operating_regions=(OperatingRegion.HIGH_LOAD, OperatingRegion.FULL_LOAD),
            recommendation="Supply the manufacturer's current technical data for the exact fuel product.",
            blocking=True,
        )
        return None

    if fuel_type in (FuelType.OTHER, FuelType.UNKNOWN):
        collector.add(
            code="CUSTOM_FUEL_PROPERTIES_REQUIRED",
            title="Fuel chemistry is not characterized",
            message=(
                "The selected fuel has no canonical reference profile. Explicit stoichiometric AFR, "
                "density, and lower heating value are required."
            ),
            severity=FindingSeverity.BLOCKING,
            affected_fields=(
                "fuel_system.fuel.stoichiometric_afr",
                "fuel_system.fuel.density_kg_per_l",
                "fuel_system.fuel.lower_heating_value_mj_per_kg",
            ),
            recommendation="Provide measured or manufacturer-specified chemistry properties.",
            blocking=True,
        )
        return None

    return None


def _resolve_property(
    explicit: EngineeringValue[float],
    profile_value: float | None,
    *,
    property_name: str,
    assumptions: list[str],
    evidence_ids: set[str],
) -> float | None:
    explicit_value = _engineering_value_number(explicit)
    if explicit_value is not None:
        evidence_ids.update(explicit.evidence_ids)
        if explicit.assumed:
            assumptions.append(f"{property_name} was supplied as an explicit assumption.")
        return explicit_value

    if profile_value is not None:
        assumptions.append(f"{property_name} was obtained from the selected reference fuel profile.")
        return float(profile_value)

    return None


def recommended_lambda_guidance(
    fuel_type: FuelType,
    *,
    charge_cooling_index: float | None,
    cold_start_difficulty_index: float | None,
) -> list[LambdaGuidance]:
    """
    Return conservative chemistry-only lambda bands.

    These are not engine-specific targets. Airflow, combustion, thermal,
    mechanical, emissions, and observed-vehicle evidence must refine them.
    """
    cooling = charge_cooling_index if charge_cooling_index is not None else 0.5
    cold = cold_start_difficulty_index if cold_start_difficulty_index is not None else 0.5

    full_load_nominal = 0.84
    if fuel_type in (FuelType.E85, FuelType.FLEX_FUEL, FuelType.ETHANOL):
        full_load_nominal = 0.82 if cooling >= 0.75 else 0.84
    elif fuel_type is FuelType.METHANOL:
        full_load_nominal = 0.78

    cold_nominal = _clamp(0.90 - cold * 0.12, 0.74, 0.90)

    return [
        LambdaGuidance(
            operating_region=OperatingRegion.CRUISE,
            minimum_lambda=0.98,
            nominal_lambda=1.00,
            maximum_lambda=1.02,
            rationale="Stoichiometric operation is the chemistry reference for stable closed-loop cruise.",
        ),
        LambdaGuidance(
            operating_region=OperatingRegion.MODERATE_LOAD,
            minimum_lambda=0.90,
            nominal_lambda=0.94,
            maximum_lambda=0.99,
            rationale="Moderate enrichment may support torque and temperature control; engine evidence must decide.",
        ),
        LambdaGuidance(
            operating_region=OperatingRegion.FULL_LOAD,
            minimum_lambda=max(0.68, full_load_nominal - 0.06),
            nominal_lambda=full_load_nominal,
            maximum_lambda=min(0.92, full_load_nominal + 0.05),
            rationale=(
                "Chemistry supports an enriched full-load region, but the final target depends on "
                "airflow, combustion stability, charge temperature, exhaust temperature, and hardware limits."
            ),
        ),
        LambdaGuidance(
            operating_region=OperatingRegion.COLD_OPERATION,
            minimum_lambda=max(0.68, cold_nominal - 0.08),
            nominal_lambda=cold_nominal,
            maximum_lambda=min(0.95, cold_nominal + 0.05),
            rationale="Cold-start enrichment requirement rises with vaporization difficulty.",
        ),
    ]


def build_fuel_state(
    configuration_or_specification: BaseMapConfiguration | FuelSpecification,
) -> FuelState:
    """Resolve canonical fuel chemistry from configuration or fuel specification."""
    if isinstance(configuration_or_specification, BaseMapConfiguration):
        specification = configuration_or_specification.fuel_system.fuel
    elif isinstance(configuration_or_specification, FuelSpecification):
        specification = configuration_or_specification
    else:
        raise TypeError(
            "build_fuel_state expects BaseMapConfiguration or FuelSpecification."
        )

    collector = _FuelFindingCollector()
    profile = _reference_profile_for_specification(specification, collector)

    assumptions: list[str] = list(profile.assumptions) if profile else []
    evidence_ids: set[str] = set()

    stoich = _resolve_property(
        specification.stoichiometric_afr,
        profile.stoichiometric_afr if profile else None,
        property_name="Stoichiometric AFR",
        assumptions=assumptions,
        evidence_ids=evidence_ids,
    )
    density_reference = _resolve_property(
        specification.density_kg_per_l,
        profile.density_kg_per_l_at_15c if profile else None,
        property_name="Fuel density",
        assumptions=assumptions,
        evidence_ids=evidence_ids,
    )
    lhv = _resolve_property(
        specification.lower_heating_value_mj_per_kg,
        profile.lower_heating_value_mj_per_kg if profile else None,
        property_name="Lower heating value",
        assumptions=assumptions,
        evidence_ids=evidence_ids,
    )
    ron = _resolve_property(
        specification.research_octane_number,
        profile.research_octane_number if profile else None,
        property_name="Research octane number",
        assumptions=assumptions,
        evidence_ids=evidence_ids,
    )
    mon = _resolve_property(
        specification.motor_octane_number,
        profile.motor_octane_number if profile else None,
        property_name="Motor octane number",
        assumptions=assumptions,
        evidence_ids=evidence_ids,
    )
    ethanol_pct = _resolve_property(
        specification.ethanol_content_pct,
        profile.typical_ethanol_pct if profile else None,
        property_name="Ethanol content",
        assumptions=assumptions,
        evidence_ids=evidence_ids,
    )
    fuel_temperature = _engineering_value_number(specification.fuel_temperature_c)
    evidence_ids.update(specification.fuel_temperature_c.evidence_ids)

    density = density_reference
    density_reference_temperature = REFERENCE_TEMPERATURE_C if density_reference is not None else None
    if density_reference is not None and fuel_temperature is not None:
        density = density_at_temperature(
            density_reference,
            fuel_temperature,
            expansion_per_c=(
                profile.density_expansion_per_c
                if profile
                else DEFAULT_DENSITY_THERMAL_EXPANSION_PER_C
            ),
        )
        assumptions.append(
            "Fuel density was temperature-corrected with a linear expansion approximation."
        )

    energy_per_l = (
        volumetric_energy_density(lhv, density)
        if lhv is not None and density is not None
        else None
    )

    if stoich is None or stoich <= 0.0:
        collector.add(
            code="STOICHIOMETRY_UNRESOLVED",
            title="Stoichiometric AFR is unresolved",
            message="Lambda cannot be translated to AFR without a valid stoichiometric AFR.",
            severity=FindingSeverity.BLOCKING,
            affected_fields=("fuel_system.fuel.stoichiometric_afr",),
            recommendation="Supply measured or manufacturer-specified stoichiometric AFR.",
            blocking=True,
        )

    if density is None or density <= 0.0:
        collector.add(
            code="DENSITY_UNRESOLVED",
            title="Fuel density is unresolved",
            message="Fuel mass and volume cannot be related without valid density evidence.",
            severity=FindingSeverity.BLOCKING,
            affected_fields=("fuel_system.fuel.density_kg_per_l",),
            recommendation="Supply density and its reference temperature.",
            blocking=True,
        )

    if lhv is None or lhv <= 0.0:
        collector.add(
            code="HEATING_VALUE_UNRESOLVED",
            title="Lower heating value is unresolved",
            message="Fuel energy content cannot be evaluated without lower heating value.",
            severity=FindingSeverity.WARNING,
            affected_fields=("fuel_system.fuel.lower_heating_value_mj_per_kg",),
            recommendation="Supply manufacturer or laboratory lower-heating-value evidence.",
        )

    if specification.fuel_type in (FuelType.E85, FuelType.FLEX_FUEL) and ethanol_pct is None:
        collector.add(
            code="ETHANOL_MEASUREMENT_REQUIRED",
            title="Ethanol content measurement required",
            message=(
                "Alcohol-blend stoichiometry, density, cold-start behavior, and fuel demand vary with composition."
            ),
            severity=FindingSeverity.WARNING,
            affected_fields=("fuel_system.fuel.ethanol_content_pct",),
            operating_regions=(OperatingRegion.COLD_OPERATION, OperatingRegion.FULL_LOAD),
            recommendation="Use measured ethanol content before high-load construction.",
        )

    if ron is None or mon is None:
        collector.add(
            code="OCTANE_EVIDENCE_INCOMPLETE",
            title="Knock-resistance evidence is incomplete",
            message=(
                "Fuel chemistry does not contain both explicit RON and MON values. "
                "No numeric anti-knock index will be inferred."
            ),
            severity=FindingSeverity.CAUTION,
            affected_fields=(
                "fuel_system.fuel.research_octane_number",
                "fuel_system.fuel.motor_octane_number",
            ),
            operating_regions=(OperatingRegion.HIGH_LOAD, OperatingRegion.FULL_LOAD),
            recommendation="Provide current product-specific octane evidence where ignition reasoning requires it.",
        )

    charge_cooling = profile.charge_cooling_index if profile else None
    cold_start = profile.cold_start_difficulty_index if profile else None
    stability = profile.combustion_stability_index if profile else None

    guidance = recommended_lambda_guidance(
        specification.fuel_type,
        charge_cooling_index=charge_cooling,
        cold_start_difficulty_index=cold_start,
    )

    return FuelState(
        fuel_type=specification.fuel_type,
        profile_id=profile.profile_id if profile else None,
        display_name=profile.display_name if profile else specification.fuel_type.value,
        stoichiometric_afr=stoich,
        density_kg_per_l=density,
        density_reference_temperature_c=density_reference_temperature,
        fuel_temperature_c=fuel_temperature,
        lower_heating_value_mj_per_kg=lhv,
        volumetric_energy_mj_per_l=energy_per_l,
        latent_heat_kj_per_kg=profile.latent_heat_kj_per_kg if profile else None,
        oxygen_mass_fraction=profile.oxygen_mass_fraction if profile else None,
        research_octane_number=ron,
        motor_octane_number=mon,
        anti_knock_index=anti_knock_index(ron, mon),
        ethanol_content_pct=ethanol_pct,
        charge_cooling_index=charge_cooling,
        cold_start_difficulty_index=cold_start,
        combustion_stability_index=stability,
        lambda_guidance=guidance,
        assumptions=assumptions,
        evidence_ids=sorted(evidence_ids),
        findings=collector.findings,
    )


def resolve_fuel_state(
    configuration_or_specification: BaseMapConfiguration | FuelSpecification,
) -> FuelState:
    """Orchestration alias for build_fuel_state."""
    return build_fuel_state(configuration_or_specification)


__all__ = [
    "FUEL_ENGINE_VERSION",
    "REFERENCE_TEMPERATURE_C",
    "FuelChemistryError",
    "FuelProfile",
    "LambdaGuidance",
    "FuelState",
    "REFERENCE_PROFILES",
    "lambda_to_afr",
    "afr_to_lambda",
    "density_at_temperature",
    "volumetric_energy_density",
    "anti_knock_index",
    "blend_gasoline_ethanol_profile",
    "recommended_lambda_guidance",
    "build_fuel_state",
    "resolve_fuel_state",
]