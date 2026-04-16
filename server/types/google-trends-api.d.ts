declare module "google-trends-api" {
  interface InterestOverTimeOpts {
    keyword: string | string[];
    startTime?: Date;
    endTime?: Date;
    geo?: string;
    hl?: string;
    timezone?: number;
  }

  const googleTrends: {
    interestOverTime(
      opts: InterestOverTimeOpts,
      cb?: (err: Error | null, results?: string) => void,
    ): Promise<string>;
  };
  export default googleTrends;
}
