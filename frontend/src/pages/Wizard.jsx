import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import WizardStepper from "@/components/WizardStepper";
import IntakeStep from "@/pages/wizard/IntakeStep";
import SafetyStep from "@/pages/wizard/SafetyStep";
import GenerateStep from "@/pages/wizard/GenerateStep";
import ReviewStep from "@/pages/wizard/ReviewStep";
import SaveStep from "@/pages/wizard/SaveStep";

const DEFAULT_INTAKE = {
  displacement_l: 2.0,
  cylinders: 4,
  induction: "Turbo",
  fuel_type: "93",
  target_hp: 350,
  rev_limit: 7000,
  injector_cc: 650,
  compression_ratio: 9.5,
  map_sensor_kpa: 250,
  intercooler_class: "Stock",
  induction_strategy: "SD",
  spool_rpm: 3000,
  intended_use: "street",
  drivetrain: "AWD",
  transmission: "Manual",
  idle_quality: "balanced",
  drivability_priority: "balanced",
  climate: "temperate",
  ethanol_pct: null,
  turbo_class: "Medium frame (~64mm)",
  boost_target_pref_kpa: null,
  hardware_preset: null,
};

const DEFAULT_ADJUSTMENTS = {
  afr_bias: 0.0,
  timing_bias: 0.0,
  boost_intent: 0.0,
  drivability_bias: 0.0,
  knock_pull_zones: [
    [0, 0, 0, 0],
    [0, 0, 0, 0],
    [0, 0, 0, 0],
    [0, 0, 0, 0],
  ],
};

export default function Wizard() {
  const [step, setStep] = useState(1);
  const [intake, setIntake] = useState(DEFAULT_INTAKE);
  const [envelope, setEnvelope] = useState(null);
  const [tune, setTune] = useState(null);
  const [adjustments, setAdjustments] = useState(DEFAULT_ADJUSTMENTS);
  const [history, setHistory] = useState([]); // [{ tune, adjustments, ts }]
  const navigate = useNavigate();

  const goto = (n) => setStep(n);

  return (
    <div data-testid="wizard-page">
      <WizardStepper current={step} onJump={(s) => s < step && goto(s)} />
      <div className="max-w-[1600px] mx-auto px-6 py-6">
        {step === 1 && (
          <IntakeStep
            intake={intake}
            setIntake={setIntake}
            onNext={() => goto(2)}
            onCancel={() => navigate("/")}
          />
        )}
        {step === 2 && (
          <SafetyStep
            intake={intake}
            envelope={envelope}
            setEnvelope={setEnvelope}
            onBack={() => goto(1)}
            onNext={() => goto(3)}
          />
        )}
        {step === 3 && (
          <GenerateStep
            intake={intake}
            adjustments={adjustments}
            tune={tune}
            setTune={(t) => {
              setTune(t);
              setHistory((h) => [{ tune: t, adjustments, ts: new Date().toISOString(), note: "Initial generation" }, ...h]);
            }}
            onBack={() => goto(2)}
            onNext={() => goto(4)}
          />
        )}
        {step === 4 && (
          <ReviewStep
            intake={intake}
            tune={tune}
            setTune={setTune}
            adjustments={adjustments}
            setAdjustments={setAdjustments}
            history={history}
            setHistory={setHistory}
            onBack={() => goto(3)}
            onNext={() => goto(5)}
          />
        )}
        {step === 5 && (
          <SaveStep
            intake={intake}
            tune={tune}
            adjustments={adjustments}
            onBack={() => goto(4)}
          />
        )}
      </div>
    </div>
  );
}
