# Building energy

This reference covers the building-energy instances of physical modelling and units: heat-transfer and psychrometric relations, zone and system energy balances, IP and SI conversions, the time conventions of EnergyPlus inputs and outputs (hour-ending time stamps, leap years, daylight saving time, aggregation across timesteps and reporting frequencies), and the units of EnergyPlus output variables and meters. It complements `dimensions/physical-modelling-and-units.md` of `sci-review`, whose general checks still apply. It excludes style, naming, performance and lint, and the schema and integrity defects of model files, which the domain checks of `checks.md` report.

## Checks

1. **Heat-transfer relations.** Check conduction (`U * A * dT`), surface convection (`h * A * dT`), long-wave radiation (`eps * sigma * A * (T1**4 - T2**4)`, in kelvin), solar gains (`SHGC * A * I`) and air exchange (`rho * cp * V_dot * dT`) against their standard forms: the driving difference has the right sign and endpoints, absolute temperatures enter every nonlinear law, and U-values combine layer resistances in series (`1 / sum(R)`) rather than conductivities in sum. Evidence: an input for which the computed heat flow differs from the standard form, and both values.
2. **Psychrometric relations.** Check humidity ratio (`W = 0.621945 * p_w / (p - p_w)`), moist-air enthalpy (`h = 1.006 * t + W * (2501 + 1.86 * t)` kJ/kg, `t` in degrees Celsius), relative humidity, dew point and saturation pressure: a consistent pressure (site barometric pressure, not always sea level), consistent units (kPa versus Pa, kg/kg versus g/kg) and a saturation correlation valid over the temperatures reached (over ice below 0 degrees Celsius). Evidence: a state point and the property computed, compared with the ASHRAE Handbook of Fundamentals value.
3. **Zone and system energy balances.** Check that the terms of a zone or system balance (conduction, solar, internal gains, infiltration, ventilation, HVAC, storage) sum to zero within tolerance, use one sign convention (heat into the zone positive) and are not counted twice (for example, a sensible load reported once as a zone load and again as a coil load). Evidence: a period over which the computed balance residual exceeds the tolerance, and its size.
4. **IP and SI conversions.** Check every conversion factor and its direction: 1 kBtu = 0.29307107 kWh (1 kWh = 3.412141633 kBtu); 1 therm = 100 kBtu = 29.307107 kWh; 1 Btu/h = 0.29307107 W; 1 ton of refrigeration = 12,000 Btu/h = 3.5168528 kW; 1 ft² = 0.09290304 m²; 1 cfm = 0.00047194745 m³/s; `t_C = (t_F - 32) / 1.8` for temperatures, `dt_K = dt_F / 1.8` for differences. Evidence: an input value and the converted value, compared with the value from the exact factor.
5. **Hour-ending time stamps.** EnergyPlus reports each interval at its end, and EPW hour `h` (1 to 24) covers the interval from `h - 1` to `h`, with hour 24 the last hour of its own day. idfkit keeps these conventions: `SQLResult.get_timeseries` returns interval-end `datetime` values (hour 24 becomes 00:00 of the next day), and the EPW readers return the `hour` column as written. Check that code assigning values to clock hours, tariff periods, occupancy windows or days shifts by one interval exactly once. Evidence: a value whose interval is known (for example, the 08:00 to 09:00 interval) and the bin or period it is assigned to.
6. **Leap years.** Check that annual series accept 8,784 hours (366 days) as well as 8,760: actual-year (AMY) weather files and run periods for leap years carry February 29. Look for hard-coded 8760 or 365 used to truncate, reshape or index a series. Evidence: a leap-year input and the hours dropped or misplaced (for example, December 31 removed by truncation to 8,760 values).
7. **Daylight saving time.** EnergyPlus and EPW data are in local standard time; daylight saving time shifts schedules, not the time stamps of the output. Check that code converting to clock time or UTC uses the EPW time zone and applies daylight saving time only where intended, and that local days of 23 or 25 hours are not assumed to have 24. Evidence: a date at a daylight saving time transition and the misaligned or duplicated hour.
8. **Aggregation across timesteps and frequencies.** Check that energies (J, kWh) are summed and rates and states (W, degrees Celsius, percent) are averaged when moving from timestep to hourly, daily, monthly or annual values; that timestep values are weighted by timestep length; and that a power is obtained from an energy by dividing by the interval length in seconds (`W = J / 3600` for hourly values). Evidence: a series and the aggregate computed, compared with the correct aggregate.
9. **Output units.** EnergyPlus reports energy output variables and meters in joules and rates in watts, at the frequency requested in the model. Check that values are converted from the reported units (`kWh = J / 3.6e6`) and that the frequency assumed by the code matches the reported one. Evidence: a reported value, its units and frequency, and the quantity the code derives from it.

## Severity guidance

The severities are those defined by the skill:

- **High:** produces a wrong result under realistic inputs.
- **Medium:** produces a wrong result only under plausible edge-case inputs, or prevents reproduction of a result.
- **Low:** a latent risk that does not currently produce a wrong result.

Typical mapping:

| Defect | Severity |
|---|---|
| Wrong or inverted IP and SI conversion factor on the main computational path | High |
| Hour-ending time stamps read as hour-starting in profiles, tariffs or peak attribution | High |
| Energies averaged or rates summed across timesteps or reporting periods | High |
| Absolute temperature in degrees Celsius in a radiation or ideal-gas relation | High |
| Annual series truncated or reshaped to 8,760 hours, wrong only for leap-year input | Medium |
| Clock-time conversion that is wrong only on the two daylight saving time transition days | Medium |
| Psychrometric correlation used below 0 degrees Celsius without the over-ice form, outside the documented range | Medium |
| Conversion factor carried only by an identifier name, with every current caller consistent | Low |

## Not defects

- **Celsius differences in linear relations.** `U * A * (t_in_c - t_out_c)` is correct; a difference of 1 degree Celsius equals 1 K.
- **Rounded factors.** A factor that agrees with the exact one to the precision reported, such as 0.29307 kWh per kBtu or 3.412 kBtu per kWh used as a divisor, is correct.
- **Documented typical-year guards.** A function that rejects any series whose length is not 8,760, with a stated error, is correct for typical-year (TMY) input; it is a defect only when the scope also feeds it leap-year data.
- **EnergyPlus reference year.** idfkit stamps time series without a calendar year with the non-leap reference year 2017; ordering or binning values within one year by these stamps is correct.
- **Case-insensitive names.** EnergyPlus resolves object names case-insensitively, so a reference `exterior wall` to an object named `Exterior Wall` is correct.
- **Standard-time output.** Leaving EnergyPlus output in local standard time is correct when the code documents that it works in standard time.

## Worked examples

### Defect 1: hour-ending time stamp read as hour-starting (High)

Trigger: an hourly `Zone Lights Electricity Energy` series for lights on from 08:00 to 18:00, read with idfkit. The 08:00 to 09:00 interval is stamped 09:00, and the 17:00 to 18:00 interval 18:00. Wrong output: the hour-of-day profile places the ten lit hours in bins 9 to 18 instead of 8 to 17, so one tenth of the lighting energy moves out of a 08:00 to 18:00 tariff window into the following hour, and the last interval of the year (stamped 00:00 on January 1 of the following year) lands in bin 0. Fix: shift each stamp back by one reporting interval before binning.

```python
from idfkit.simulation import SQLResult

def hourly_profile(sql: SQLResult, variable: str, key: str) -> list[float]:
    ts = sql.get_timeseries(variable, key, frequency="Hourly")
    profile = [0.0] * 24
    for t, v in zip(ts.timestamps, ts.values):
        profile[t.hour] += v  # defect: t is the end of the interval
    return profile
# Fix: profile[(t - timedelta(hours=1)).hour] += v
```

```typescript
import { parseEpw } from '@idfkit/weather';

function hourlyMeanDryBulb(text: string): number[] {
  const { hours } = parseEpw(text);
  const sum = new Array<number>(24).fill(0);
  for (let i = 0; i < hours.rowCount; i++) {
    sum[hours.hour[i] % 24] += hours.dryBulbTemperature[i]; // defect: EPW hour 1 is 00:00 to 01:00
  }
  return sum.map((s) => s / (hours.rowCount / 24));
}
// Fix: sum[hours.hour[i] - 1] += hours.dryBulbTemperature[i];
```

### Defect 2: kBtu converted to kWh with an inverted factor (High)

Trigger: a monthly utility bill of 1,000 kBtu compared with the simulated electricity meter. Wrong output: the bill is converted to 3,412 kWh instead of 293.07 kWh, a factor of 11.64, so the calibration error is reported as about -91% when the model matches the bill. Fix: multiply by 0.29307107, or divide by 3.412141633.

```python
from idfkit.simulation import SQLResult

KWH_PER_KBTU = 3.412  # defect: this is kBtu per kWh

def monthly_error(sql: SQLResult, bill_kbtu: list[float]) -> list[float]:
    meter = sql.get_timeseries("Electricity:Facility", frequency="Monthly")  # joules
    simulated_kwh = [j / 3.6e6 for j in meter.values]
    billed_kwh = [b * KWH_PER_KBTU for b in bill_kbtu]
    return [(s - b) / b for s, b in zip(simulated_kwh, billed_kwh)]
# Fix: KWH_PER_KBTU = 0.29307107
```

```typescript
import type { WeatherFile } from '@idfkit/weather';

export type Site = { weather: WeatherFile; billKbtu: number[] };

export function billedKwh(site: Site): number[] {
  return site.billKbtu.map((kbtu) => kbtu / 0.29307107); // defect: divides by kWh per kBtu
}
// Fix: kbtu * 0.29307107
```

### Defect 3: leap-year series truncated to 8,760 hours (Medium)

Trigger: an actual-year EPW for 2024, which has 8,784 hourly records. Wrong output: truncation to the first 8,760 values drops December 31, so heating degree-hours omit one winter day (for a day at a mean of 0 degrees Celsius and a base of 18 degrees Celsius, 432 degree-hours, about 0.6% of a 70,000 degree-hour climate). Fix: iterate over every record (`row_count` or `rowCount`), or reject non-8,760 input explicitly if only typical years are supported.

```python
from idfkit.weather import load_epw

def heating_degree_hours(path: str, base_c: float = 18.0) -> float:
    temps = load_epw(path).hours.dry_bulb_temperature[:8760]  # defect: drops Dec 31 in a leap year
    return sum(max(0.0, base_c - t) for t in temps)
# Fix: temps = load_epw(path).hours.dry_bulb_temperature
```

```typescript
import { parseEpw } from '@idfkit/weather';

function heatingDegreeHours(text: string, baseC = 18): number {
  const t = parseEpw(text).hours.dryBulbTemperature;
  let total = 0;
  for (let i = 0; i < 8760; i++) total += Math.max(0, baseC - t[i]); // defect: drops Dec 31 in a leap year
  return total;
}
// Fix: for (let i = 0; i < t.length; i++)
```

### Look-alike: correct conversion by division and correct EPW hour shift (not a defect)

Trigger considered: 1,000 kBtu, and EPW hour 1. Output: 293.07 kWh, the exact value, because dividing by kBtu per kWh equals multiplying by kWh per kBtu; and bin 0 for the interval from 00:00 to 01:00, which is correct. No fix is required; record the items as checked and found correct.

```python
from idfkit.weather import load_epw

KBTU_PER_KWH = 3.412141633

def kbtu_to_kwh(kbtu: float) -> float:
    return kbtu / KBTU_PER_KWH  # correct: division by kBtu per kWh

def hour_of_day(path: str) -> list[int]:
    return [int(h) - 1 for h in load_epw(path).hours.hour]  # correct: hour-ending shifted once
```

```typescript
import { parseEpw } from '@idfkit/weather';

const KWH_PER_KBTU = 0.29307107;
export const kbtuToKwh = (kbtu: number): number => kbtu * KWH_PER_KBTU; // correct

export function hourOfDay(text: string): number[] {
  return Array.from(parseEpw(text).hours.hour, (h) => h - 1); // correct: hour-ending shifted once
}
```
