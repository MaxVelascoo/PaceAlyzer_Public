export type Lap = {
  index: number;
  name: string;
  elapsed_time: number;
  distance: number;
  avg_watts: number | null;
  avg_hr: number | null;
  max_hr: number | null;
  avg_speed: number | null;
};

export type Training = {
  activity_id: number;
  name?: string | null;
  type?: string | null;
  date: string;
  duration: number | null;
  distance: number | null;
  avgheartrate: number | null;
  weighted_average_watts: number | null;
  altitude?: number | null;
  TSS?: number | null;
  power_stream?: number[] | null;
  hr_stream?: number[] | null;
  time_stream?: number[] | null;
  laps?: Lap[] | null;
};
