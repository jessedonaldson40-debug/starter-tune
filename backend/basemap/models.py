"""
StandAIlone BaseMap Constructor
===============================

Canonical engineering models for the BaseMap Constructor kernel.

This module defines the contracts shared by every BaseMap Constructor
engineering discipline:

- configuration intake
- evidence and provenance
- pressure representation
- engine geometry
- airflow hardware
- forced-induction hardware
- fuel and injector systems
- sensor definitions
- mechanical capability
- thermal capability
- operating targets
- authority decisions
- confidence assessments
- calibration tables
- engineering findings
- construction results

Architecture rule
-----------------
This module contains data contracts only.

It must not:
- construct calibration values,
- estimate airflow,
- calculate fuel mass,
- calculate ignition timing,
- infer mechanical limits,
- grant authority,
- read files,
- write files,
- call external services.

Those responsibilities belong to their dedicated engineering modules.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Generic, TypeVar


# ============================================================================
# ENUMERATIONS
# ============================================================================


class StrEnum(str, Enum):
    """
    String-backed enum suitable for JSON serialization.
    """

    def __str__(self) -> str:
        return self.value


class EvidenceSource(StrEnum):
    USER_DECLARED = "user_declared"
    MANUFACTURER_SPECIFICATION = "manufacturer_specification"
    MEASURED = "measured"
    TELEMETRY = "telemetry"
    INSPECTOR = "inspector"
    SIMULATION = "simulation"
    ENGINE_FAMILY_REFERENCE = "engine_family_reference"
    CALCULATED = "calculated"
    ASSUMED = "assumed"
    UNKNOWN = "unknown"


class EvidenceQuality(StrEnum):
    VERIFIED = "verified"
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    UNVERIFIED = "unverified"
    UNKNOWN = "unknown"


class UnitSystem(StrEnum):
    METRIC = "metric"
    IMPERIAL = "imperial"


class PressureReference(StrEnum):
    ABSOLUTE = "absolute"
    GAUGE = "gauge"
    DIFFERENTIAL = "differential"


class PressureUnit(StrEnum):
    KPA = "kpa"
    BAR = "bar"
    PSI = "psi"


class TemperatureUnit(StrEnum):
    CELSIUS = "celsius"
    FAHRENHEIT = "fahrenheit"
    KELVIN = "kelvin"


class InductionType(StrEnum):
    NATURALLY_ASPIRATED = "naturally_aspirated"
    TURBOCHARGED = "turbocharged"
    SUPERCHARGED = "supercharged"


class SuperchargerType(StrEnum):
    ROOTS = "roots"
    TWIN_SCREW = "twin_screw"
    CENTRIFUGAL = "centrifugal"
    OTHER = "other"
    UNKNOWN = "unknown"


class TurboHousingType(StrEnum):
    OPEN = "open"
    DIVIDED = "divided"
    V_BAND = "v_band"
    OTHER = "other"
    UNKNOWN = "unknown"


class WastegateType(StrEnum):
    INTERNAL = "internal"
    EXTERNAL = "external"
    ELECTRONIC = "electronic"
    UNKNOWN = "unknown"


class FuelRegulatorType(StrEnum):
    RETURN = "return"
    RETURNLESS = "returnless"
    MECHANICAL_RETURN = "mechanical_return"
    ELECTRONIC_RETURNLESS = "electronic_returnless"
    UNKNOWN = "unknown"


class FuelType(StrEnum):
    GASOLINE = "gasoline"
    E85 = "e85"
    FLEX_FUEL = "flex_fuel"
    METHANOL = "methanol"
    ETHANOL = "ethanol"
    RACE_GASOLINE = "race_gasoline"
    OTHER = "other"
    UNKNOWN = "unknown"


class CamControlType(StrEnum):
    FIXED = "fixed"
    VTEC = "vtec"
    VARIABLE_INTAKE = "variable_intake"
    VARIABLE_EXHAUST = "variable_exhaust"
    DUAL_VARIABLE = "dual_variable"
    MULTI_PROFILE_VARIABLE = "multi_profile_variable"
    UNKNOWN = "unknown"


class TableValueType(StrEnum):
    VOLUMETRIC_EFFICIENCY = "volumetric_efficiency"
    FUEL_MASS = "fuel_mass"
    INJECTOR_PULSE_WIDTH = "injector_pulse_width"
    LAMBDA_TARGET = "lambda_target"
    AFR_TARGET = "afr_target"
    IGNITION_ADVANCE = "ignition_advance"
    MANIFOLD_PRESSURE_TARGET = "manifold_pressure_target"
    BOOST_PRESSURE_TARGET = "boost_pressure_target"
    WASTEGATE_DUTY = "wastegate_duty"
    IDLE_SPEED = "idle_speed"
    STARTUP_ENRICHMENT = "startup_enrichment"
    OTHER = "other"


class AuthorityLevel(StrEnum):
    DENIED = "denied"
    OBSERVATION_ONLY = "observation_only"
    RESTRICTED = "restricted"
    CONDITIONAL = "conditional"
    GRANTED = "granted"
    VALIDATED = "validated"


class OperatingRegion(StrEnum):
    CRANKING = "cranking"
    STARTUP = "startup"
    IDLE = "idle"
    DECELERATION = "deceleration"
    LIGHT_LOAD = "light_load"
    CRUISE = "cruise"
    MODERATE_LOAD = "moderate_load"
    HIGH_LOAD = "high_load"
    BOOST_ENTRY = "boost_entry"
    FULL_LOAD = "full_load"
    HIGH_RPM = "high_rpm"
    OVERREV = "overrev"
    COLD_OPERATION = "cold_operation"
    THERMALLY_LIMITED = "thermally_limited"


class FindingSeverity(StrEnum):
    INFORMATION = "information"
    CAUTION = "caution"
    WARNING = "warning"
    DANGER = "danger"
    BLOCKING = "blocking"


class FindingDisposition(StrEnum):
    PRESERVE = "preserve"
    STRENGTHEN = "strengthen"
    REFACTOR = "refactor"
    RECONSIDER = "reconsider"
    CANONICAL = "canonical"


class ConfidenceDimension(StrEnum):
    INPUT_COMPLETENESS = "input_completeness"
    DATA_QUALITY = "data_quality"
    MODEL_APPLICABILITY = "model_applicability"
    PHYSICAL_FEASIBILITY = "physical_feasibility"
    CONSTRUCTION_CONFIDENCE = "construction_confidence"
    VALIDATION_CONFIDENCE = "validation_confidence"
    OBSERVED_VEHICLE_CONFIDENCE = "observed_vehicle_confidence"


class ConstructionStatus(StrEnum):
    NOT_STARTED = "not_started"
    BLOCKED = "blocked"
    PARTIAL = "partial"
    CONSTRUCTED = "constructed"
    VALIDATION_REQUIRED = "validation_required"
    VALIDATED = "validated"
    FAILED = "failed"


# ============================================================================
# COMMON ENGINEERING VALUE TYPES
# ============================================================================


T = TypeVar("T")


@dataclass(slots=True)
class EvidenceRecord:
    """
    Evidence supporting an input, assumption, calculation, or decision.
    """

    evidence_id: str
    source: EvidenceSource
    quality: EvidenceQuality
    description: str

    source_reference: str | None = None
    measured_at_iso_utc: str | None = None
    notes: str | None = None

    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EngineeringValue(Generic[T]):
    """
    A value accompanied by its engineering provenance.

    This avoids treating:
    - measured values,
    - manufacturer specifications,
    - user declarations,
    - calculations,
    - and assumptions

    as though they possess equal authority.
    """

    value: T | None
    source: EvidenceSource = EvidenceSource.UNKNOWN
    quality: EvidenceQuality = EvidenceQuality.UNKNOWN

    unit: str | None = None
    evidence_ids: list[str] = field(default_factory=list)

    assumed: bool = False
    required: bool = False
    notes: str | None = None


@dataclass(slots=True)
class PressureValue:
    """
    Explicit pressure quantity.

    Pressure reference is mandatory because a value such as "200 kPa"
    is unsafe and ambiguous without declaring whether it is absolute,
    gauge, or differential pressure.
    """

    value: float
    unit: PressureUnit
    reference: PressureReference

    reference_pressure_kpa: float | None = None
    source: EvidenceSource = EvidenceSource.UNKNOWN
    quality: EvidenceQuality = EvidenceQuality.UNKNOWN

    evidence_ids: list[str] = field(default_factory=list)
    notes: str | None = None


@dataclass(slots=True)
class TemperatureValue:
    value: float
    unit: TemperatureUnit

    source: EvidenceSource = EvidenceSource.UNKNOWN
    quality: EvidenceQuality = EvidenceQuality.UNKNOWN

    evidence_ids: list[str] = field(default_factory=list)
    notes: str | None = None


# ============================================================================
# ENGINE CONFIGURATION
# ============================================================================


@dataclass(slots=True)
class EngineGeometry:
    engine_family: EngineeringValue[str] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    displacement_l: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(
            value=None,
            unit="L",
            required=True,
        )
    )

    cylinders: EngineeringValue[int] = field(
        default_factory=lambda: EngineeringValue(
            value=None,
            required=True,
        )
    )

    bore_mm: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(
            value=None,
            unit="mm",
        )
    )

    stroke_mm: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(
            value=None,
            unit="mm",
        )
    )

    rod_length_mm: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(
            value=None,
            unit="mm",
        )
    )

    compression_ratio: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(
            value=None,
            required=True,
        )
    )

    deck_clearance_mm: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(
            value=None,
            unit="mm",
        )
    )

    head_gasket_thickness_mm: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(
            value=None,
            unit="mm",
        )
    )

    combustion_chamber_volume_cc: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(
            value=None,
            unit="cc",
        )
    )

    firing_order: EngineeringValue[str] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )


@dataclass(slots=True)
class CylinderHeadConfiguration:
    manufacturer: EngineeringValue[str] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    model: EngineeringValue[str] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    chamber_type: EngineeringValue[str] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    intake_valve_diameter_mm: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(value=None, unit="mm")
    )

    exhaust_valve_diameter_mm: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(value=None, unit="mm")
    )

    intake_flow_curve: list[tuple[float, float]] = field(default_factory=list)
    exhaust_flow_curve: list[tuple[float, float]] = field(default_factory=list)

    flow_curve_lift_unit: str = "mm"
    flow_curve_airflow_unit: str = "cfm"

    ported: EngineeringValue[bool] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    notes: str | None = None


@dataclass(slots=True)
class CamshaftSpecification:
    manufacturer: EngineeringValue[str] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    model: EngineeringValue[str] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    control_type: CamControlType = CamControlType.UNKNOWN

    intake_duration_deg: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(
            value=None,
            unit="crank_deg",
        )
    )

    exhaust_duration_deg: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(
            value=None,
            unit="crank_deg",
        )
    )

    intake_lift_mm: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(value=None, unit="mm")
    )

    exhaust_lift_mm: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(value=None, unit="mm")
    )

    lobe_separation_angle_deg: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(
            value=None,
            unit="crank_deg",
        )
    )

    intake_centerline_deg: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(
            value=None,
            unit="crank_deg",
        )
    )

    exhaust_centerline_deg: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(
            value=None,
            unit="crank_deg",
        )
    )

    low_lobe_specification: str | None = None
    high_lobe_specification: str | None = None

    notes: str | None = None


@dataclass(slots=True)
class AirPathConfiguration:
    throttle_diameter_mm: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(value=None, unit="mm")
    )

    intake_manifold_model: EngineeringValue[str] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    intake_runner_length_mm: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(value=None, unit="mm")
    )

    intake_runner_area_mm2: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(value=None, unit="mm2")
    )

    exhaust_manifold_model: EngineeringValue[str] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    exhaust_primary_diameter_mm: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(value=None, unit="mm")
    )

    exhaust_system_diameter_mm: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(value=None, unit="mm")
    )

    catalytic_converter_present: EngineeringValue[bool] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    estimated_intake_pressure_drop_kpa: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(value=None, unit="kPa")
    )

    estimated_exhaust_backpressure_ratio: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )


# ============================================================================
# FORCED INDUCTION
# ============================================================================


@dataclass(slots=True)
class TurbochargerConfiguration:
    enabled: bool = False

    manufacturer: EngineeringValue[str] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    model: EngineeringValue[str] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    compressor_map_id: EngineeringValue[str] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    compressor_inducer_mm: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(value=None, unit="mm")
    )

    compressor_exducer_mm: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(value=None, unit="mm")
    )

    turbine_inducer_mm: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(value=None, unit="mm")
    )

    turbine_exducer_mm: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(value=None, unit="mm")
    )

    turbine_housing_ar: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    housing_type: TurboHousingType = TurboHousingType.UNKNOWN
    wastegate_type: WastegateType = WastegateType.UNKNOWN

    wastegate_spring_pressure: PressureValue | None = None

    maximum_shaft_speed_rpm: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(
            value=None,
            unit="rpm",
        )
    )

    turbine_efficiency: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    compressor_efficiency_default: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    notes: str | None = None


@dataclass(slots=True)
class SuperchargerConfiguration:
    enabled: bool = False

    manufacturer: EngineeringValue[str] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    model: EngineeringValue[str] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    supercharger_type: SuperchargerType = SuperchargerType.UNKNOWN

    displacement_cc_per_rev: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(
            value=None,
            unit="cc/rev",
        )
    )

    drive_ratio: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    pulley_ratio: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    maximum_impeller_speed_rpm: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(
            value=None,
            unit="rpm",
        )
    )

    bypass_strategy: EngineeringValue[str] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    efficiency_map_id: EngineeringValue[str] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    estimated_parasitic_loss_kw: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(value=None, unit="kW")
    )

    notes: str | None = None


@dataclass(slots=True)
class IntercoolerConfiguration:
    present: bool = False

    manufacturer: EngineeringValue[str] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    model: EngineeringValue[str] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    effectiveness: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    pressure_drop_kpa: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(value=None, unit="kPa")
    )

    heat_soak_margin: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )


# ============================================================================
# FUEL AND INJECTOR SYSTEM
# ============================================================================


@dataclass(slots=True)
class FuelSpecification:
    fuel_type: FuelType = FuelType.UNKNOWN

    stoichiometric_afr: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    density_kg_per_l: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(
            value=None,
            unit="kg/L",
        )
    )

    lower_heating_value_mj_per_kg: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(
            value=None,
            unit="MJ/kg",
        )
    )

    research_octane_number: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    motor_octane_number: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    ethanol_content_pct: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(value=None, unit="%")
    )

    fuel_temperature_c: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(value=None, unit="degC")
    )


@dataclass(slots=True)
class InjectorConfiguration:
    manufacturer: EngineeringValue[str] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    model: EngineeringValue[str] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    quantity: EngineeringValue[int] = field(
        default_factory=lambda: EngineeringValue(
            value=None,
            required=True,
        )
    )

    rated_flow_cc_min: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(
            value=None,
            unit="cc/min",
            required=True,
        )
    )

    rated_pressure: PressureValue | None = None

    dead_time_table_ms: dict[float, float] = field(default_factory=dict)
    short_pulse_adder_ms: dict[float, float] = field(default_factory=dict)

    minimum_effective_pulse_width_ms: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(value=None, unit="ms")
    )

    maximum_recommended_duty_pct: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(
            value=85.0,
            source=EvidenceSource.ASSUMED,
            quality=EvidenceQuality.MODERATE,
            unit="%",
            assumed=True,
        )
    )

    staged_injection: bool = False
    secondary_injector_configuration_id: str | None = None


@dataclass(slots=True)
class FuelSystemConfiguration:
    fuel: FuelSpecification = field(default_factory=FuelSpecification)
    injectors: InjectorConfiguration = field(default_factory=InjectorConfiguration)

    base_fuel_pressure: PressureValue | None = None

    regulator_type: FuelRegulatorType = FuelRegulatorType.UNKNOWN

    fuel_pump_manufacturer: EngineeringValue[str] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    fuel_pump_model: EngineeringValue[str] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    pump_flow_curve_lph: dict[float, float] = field(default_factory=dict)

    fuel_pressure_sensor_present: bool = False

    return_line_diameter_mm: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(value=None, unit="mm")
    )

    fuel_rail_volume_cc: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(value=None, unit="cc")
    )


# ============================================================================
# SENSOR CONFIGURATION
# ============================================================================


@dataclass(slots=True)
class SensorDefinition:
    name: str
    unit: str

    manufacturer: str | None = None
    model: str | None = None

    minimum_value: float | None = None
    maximum_value: float | None = None

    calibration_id: str | None = None

    source: EvidenceSource = EvidenceSource.USER_DECLARED
    quality: EvidenceQuality = EvidenceQuality.UNVERIFIED

    required_for_authority: bool = False
    notes: str | None = None


@dataclass(slots=True)
class SensorConfiguration:
    map_sensor: SensorDefinition | None = None
    barometric_pressure_sensor: SensorDefinition | None = None
    wideband_sensor: SensorDefinition | None = None
    fuel_pressure_sensor: SensorDefinition | None = None
    oil_pressure_sensor: SensorDefinition | None = None
    oil_temperature_sensor: SensorDefinition | None = None
    exhaust_backpressure_sensor: SensorDefinition | None = None
    exhaust_gas_temperature_sensors: list[SensorDefinition] = field(
        default_factory=list
    )

    additional_sensors: list[SensorDefinition] = field(default_factory=list)


# ============================================================================
# MECHANICAL AND THERMAL CAPABILITY
# ============================================================================


@dataclass(slots=True)
class MechanicalConfiguration:
    piston_material: EngineeringValue[str] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    connecting_rod_material: EngineeringValue[str] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    connecting_rod_model: EngineeringValue[str] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    rod_bolt_specification: EngineeringValue[str] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    crankshaft_specification: EngineeringValue[str] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    bearing_clearance_specification: EngineeringValue[str] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    oil_pump_specification: EngineeringValue[str] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    harmonic_damper_specification: EngineeringValue[str] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    valve_spring_specification: EngineeringValue[str] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    retainer_material: EngineeringValue[str] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    demonstrated_rev_limit_rpm: EngineeringValue[int] = field(
        default_factory=lambda: EngineeringValue(value=None, unit="rpm")
    )

    demonstrated_torque_nm: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(value=None, unit="N*m")
    )

    demonstrated_power_kw: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(value=None, unit="kW")
    )


@dataclass(slots=True)
class ThermalConfiguration:
    cooling_system_description: EngineeringValue[str] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    radiator_description: EngineeringValue[str] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    oil_cooler_present: EngineeringValue[bool] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    maximum_coolant_temperature_c: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(value=None, unit="degC")
    )

    maximum_oil_temperature_c: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(value=None, unit="degC")
    )

    maximum_intake_air_temperature_c: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(value=None, unit="degC")
    )

    maximum_exhaust_gas_temperature_c: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(value=None, unit="degC")
    )


# ============================================================================
# OPERATING TARGETS
# ============================================================================


@dataclass(slots=True)
class OperatingTargets:
    target_power_kw: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(value=None, unit="kW")
    )

    target_torque_nm: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(value=None, unit="N*m")
    )

    requested_rev_limit_rpm: EngineeringValue[int] = field(
        default_factory=lambda: EngineeringValue(
            value=None,
            unit="rpm",
            required=True,
        )
    )

    requested_manifold_pressure_abs: PressureValue | None = None
    requested_boost_pressure_gauge: PressureValue | None = None

    target_lambda_full_load: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    target_lambda_cruise: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(value=1.0)
    )

    intended_use: EngineeringValue[str] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    street_driven: EngineeringValue[bool] = field(
        default_factory=lambda: EngineeringValue(value=None)
    )

    endurance_duration_seconds: EngineeringValue[float] = field(
        default_factory=lambda: EngineeringValue(value=None, unit="s")
    )


# ============================================================================
# COMPLETE CONFIGURATION
# ============================================================================


@dataclass(slots=True)
class BaseMapConfiguration:
    configuration_id: str
    schema_version: str

    engine: EngineGeometry
    cylinder_head: CylinderHeadConfiguration
    camshaft: CamshaftSpecification
    air_path: AirPathConfiguration

    induction_type: InductionType
    turbocharger: TurbochargerConfiguration
    supercharger: SuperchargerConfiguration
    intercooler: IntercoolerConfiguration

    fuel_system: FuelSystemConfiguration
    sensors: SensorConfiguration

    mechanical: MechanicalConfiguration
    thermal: ThermalConfiguration
    targets: OperatingTargets

    evidence: list[EvidenceRecord] = field(default_factory=list)

    vehicle_id: str | None = None
    calibration_id: str | None = None

    notes: str | None = None

    created_at_iso_utc: str | None = None
    created_by: str | None = None


# ============================================================================
# ENGINEERING FINDINGS
# ============================================================================


@dataclass(slots=True)
class EngineeringFinding:
    finding_id: str
    code: str
    title: str
    message: str

    severity: FindingSeverity
    disposition: FindingDisposition | None = None

    subsystem: str | None = None
    operating_regions: list[OperatingRegion] = field(default_factory=list)

    evidence_ids: list[str] = field(default_factory=list)
    affected_fields: list[str] = field(default_factory=list)

    recommendation: str | None = None
    constitutional_basis: str | None = None

    blocking: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


# ============================================================================
# AUTHORITY
# ============================================================================


@dataclass(slots=True)
class RegionAuthority:
    region: OperatingRegion
    level: AuthorityLevel

    reason_codes: list[str] = field(default_factory=list)
    rationale: str | None = None

    evidence_ids: list[str] = field(default_factory=list)
    required_actions: list[str] = field(default_factory=list)

    maximum_rpm: int | None = None
    maximum_load_abs_kpa: float | None = None
    maximum_boost_gauge_kpa: float | None = None

    fuel_authority: AuthorityLevel = AuthorityLevel.DENIED
    ignition_authority: AuthorityLevel = AuthorityLevel.DENIED
    boost_authority: AuthorityLevel = AuthorityLevel.DENIED


@dataclass(slots=True)
class AuthorityAssessment:
    overall_level: AuthorityLevel
    regions: list[RegionAuthority]

    granted_capabilities: list[str] = field(default_factory=list)
    denied_capabilities: list[str] = field(default_factory=list)

    findings: list[EngineeringFinding] = field(default_factory=list)

    assessment_version: str = "authority/1.0"


# ============================================================================
# CONFIDENCE
# ============================================================================


@dataclass(slots=True)
class ConfidenceScore:
    dimension: ConfidenceDimension
    score: float

    rationale: str
    evidence_ids: list[str] = field(default_factory=list)

    penalties: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ConfidenceAssessment:
    dimensions: list[ConfidenceScore]

    overall_score: float
    lowest_dimension: ConfidenceDimension

    authority_limited_by_confidence: bool
    limiting_reasons: list[str] = field(default_factory=list)

    assessment_version: str = "confidence/1.0"


# ============================================================================
# CANONICAL CALIBRATION TABLES
# ============================================================================


@dataclass(slots=True)
class AxisDefinition:
    name: str
    unit: str
    values: list[float]

    reference: PressureReference | None = None
    description: str | None = None


@dataclass(slots=True)
class CalibrationTable:
    table_id: str
    name: str
    value_type: TableValueType

    value_unit: str

    x_axis: AxisDefinition
    y_axis: AxisDefinition | None

    values: list[list[float]] | list[float]

    authority_level: AuthorityLevel

    assumptions: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    finding_ids: list[str] = field(default_factory=list)

    minimum_value: float | None = None
    maximum_value: float | None = None

    metadata: dict[str, Any] = field(default_factory=dict)


# ============================================================================
# INTERMEDIATE ENGINEERING STATES
# ============================================================================


@dataclass(slots=True)
class AirflowState:
    rpm_axis: list[float]
    load_axis_abs_kpa: list[float]

    trapped_air_mass_mg_per_cylinder: list[list[float]]
    volumetric_efficiency: list[list[float]]

    model_applicability_score: float

    assumptions: list[str] = field(default_factory=list)
    finding_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class FuelRequirementState:
    rpm_axis: list[float]
    load_axis_abs_kpa: list[float]

    target_lambda: list[list[float]]
    fuel_mass_mg_per_event: list[list[float]]

    assumptions: list[str] = field(default_factory=list)
    finding_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class InjectorFeasibilityState:
    pulse_width_ms: list[list[float]]
    injector_duty_pct: list[list[float]]

    nonlinear_region_mask: list[list[bool]]
    authority_mask: list[list[bool]]

    maximum_duty_pct: float
    minimum_pulse_width_ms: float

    assumptions: list[str] = field(default_factory=list)
    finding_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CombustionState:
    estimated_burn_duration_crank_deg: list[list[float]]
    estimated_charge_temperature_c: list[list[float]]

    knock_sensitivity_index: list[list[float]]

    assumptions: list[str] = field(default_factory=list)
    finding_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class IgnitionHypothesisState:
    ignition_advance_deg_btdc: list[list[float]]

    mbt_claimed: bool = False
    knock_limited_claimed: bool = False

    assumptions: list[str] = field(default_factory=list)
    finding_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ThermalAssessment:
    thermal_margin_score: float
    authority_limited: bool

    estimated_charge_temperature_c: list[list[float]] = field(
        default_factory=list
    )

    estimated_exhaust_temperature_c: list[list[float]] = field(
        default_factory=list
    )

    findings: list[EngineeringFinding] = field(default_factory=list)


@dataclass(slots=True)
class MechanicalAssessment:
    requested_rev_limit_rpm: int | None
    granted_rev_limit_rpm: int | None

    requested_torque_nm: float | None
    granted_torque_nm: float | None

    rpm_authority: AuthorityLevel
    torque_authority: AuthorityLevel

    mean_piston_speed_m_s: float | None = None
    peak_piston_acceleration_m_s2: float | None = None

    findings: list[EngineeringFinding] = field(default_factory=list)


# ============================================================================
# FINAL CONSTRUCTION RESULT
# ============================================================================


@dataclass(slots=True)
class ConstructionManifest:
    constructor_version: str
    schema_version: str

    configuration_id: str
    calibration_id: str

    modules_executed: list[str]

    started_at_iso_utc: str | None = None
    completed_at_iso_utc: str | None = None

    deterministic: bool = True
    random_seed: int | None = None


@dataclass(slots=True)
class BaseMapConstructionResult:
    status: ConstructionStatus

    configuration: BaseMapConfiguration
    manifest: ConstructionManifest

    authority: AuthorityAssessment
    confidence: ConfidenceAssessment

    tables: list[CalibrationTable] = field(default_factory=list)
    findings: list[EngineeringFinding] = field(default_factory=list)

    airflow_state: AirflowState | None = None
    fuel_requirement_state: FuelRequirementState | None = None
    injector_state: InjectorFeasibilityState | None = None
    combustion_state: CombustionState | None = None
    ignition_state: IgnitionHypothesisState | None = None
    thermal_assessment: ThermalAssessment | None = None
    mechanical_assessment: MechanicalAssessment | None = None

    assumptions: list[str] = field(default_factory=list)
    denied_operations: list[str] = field(default_factory=list)
    required_validation: list[str] = field(default_factory=list)

    package_metadata: dict[str, Any] = field(default_factory=dict)


# ============================================================================
# SERIALIZATION
# ============================================================================


def model_to_dict(value: Any) -> Any:
    """
    Convert BaseMap Constructor models into JSON-compatible Python values.

    This function intentionally handles:
    - dataclasses,
    - enums,
    - dictionaries,
    - lists,
    - tuples,
    - primitive values.

    It does not write files. File and package serialization belong in
    package.py.
    """

    if isinstance(value, Enum):
        return value.value

    if hasattr(value, "__dataclass_fields__"):
        return {
            key: model_to_dict(item)
            for key, item in asdict(value).items()
        }

    if isinstance(value, dict):
        return {
            str(key): model_to_dict(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [model_to_dict(item) for item in value]

    return value