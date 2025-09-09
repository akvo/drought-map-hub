import { auth } from "@/lib";
import { FeedbackSection, LogoSection, Navbar } from "@/components";
import {
  DROUGHT_CATEGORY_COLOR,
  DROUGHT_CATEGORY_VALUE,
} from "@/static/config";

const AboutPage = async () => {
  const session = await auth.getSession();
  return (
    <div className="w-full min-h-screen">
      <Navbar session={session} />
      <div className="container w-full h-full relative space-y-4 xl:space-y-8 pt-3 pb-9">
        <div className="w-full space-y-2">
          <div className="w-full">
            <h1 className="text-2xl xl:text-3xl font-bold text-gray-800">
              About the Eswatini Drought Monitor
            </h1>
          </div>
        </div>
        <p className="text-gray-700 border-b-2 border-b-neutral-400 pb-6">
          The <strong>Eswatini Drought Monitor</strong> provides a monthly
          assessment of drought conditions across the country using a
          scientifically robust indicator known as the{" "}
          <strong>Composite Drought Indicator (CDI)</strong>. The system is
          designed to offer real-time insights to everyone involved in proactive
          drought preparedness and response in the Kingdom of Eswatini.
        </p>
        <h2 className="text-xl font-semibold text-gray-800 pt-4">
          What is the Composite Drought Indicator (CDI)?
        </h2>
        <div className="text-gray-700 border-b-2 border-b-neutral-400 pb-6 space-y-4">
          <p>
            The <b>CDI</b> combines four different types of drought-relevant
            datasets into a single map that reflects the overall severity of
            drought conditions:
          </p>
          <ul className="list-disc list-inside pl-4 leading-8">
            <li>
              <strong>Land Surface Temperature (LST)</strong> – measures heat
              stress and temperature anomalies
            </li>
            <li>
              <strong>Normalized Difference Vegetation Index (NDVI)</strong> –
              captures vegetation health and greenness
            </li>
            <li>
              <strong>Standardized Precipitation Index (SPI)</strong> – assesses
              rainfall deficits
            </li>
            <li>
              <strong>Soil Moisture</strong> – reflects water availability for
              crops and plants
            </li>
          </ul>
          <p>
            These datasets are combined using a weighted average system, with
            flexibility to adjust the weights depending on regional
            characteristics or if certain data is missing.
          </p>
        </div>
        <h2 className="text-xl font-semibold text-gray-800 pt-4">
          How is the CDI Computed?
        </h2>
        <div className="text-gray-700 border-b-2 border-b-neutral-400 pb-6">
          <p>
            The CDI is generated in a mostly automated process that includes the
            following steps:
          </p>
          <ol className="list-decimal list-inside pl-4 leading-8">
            <li>
              <b>Data Retrieval</b> – The system checks for the latest datasets
              from global sources, and automatically downloads and stores LST,
              NDVI, SPI, and Soil Moisture data.
            </li>
            <li>
              <b>Processing</b> – Computes percentile ranks and long-term trends
              using 40+ years of data where available.
            </li>
            <li>
              <b>Weight Adjustment</b> – If needed, experts can change the
              weight of each dataset depending on data quality or relevance.
            </li>
            <li>
              <b>CDI Map Generation</b> – Monthly drought maps (CDI) are
              produced indicating the drought levels per Inkundla (region).
            </li>
            <li>
              <b>Validation</b> – The Technical Working Group (TWG) reviews the
              maps and provides expert feedback.
            </li>
            <li>
              <b>Final Publication</b> – Once validated, the CDI is published
              and made available to the public on this platform.
            </li>
          </ol>
        </div>
        <h2 className="text-xl font-semibold text-gray-800">
          What Do the CDI Categories Mean?
        </h2>
        <div className="w-full text-gray-700 space-y-4 border-b-2 border-b-neutral-400 pb-6">
          <p>
            CDI drought classifications are <b>relative</b>, meaning they
            compare current conditions to a <b>long-term historical baseline</b>{" "}
            for each specific location. This helps answer the question:{" "}
            <i>
              &quot;How rare or severe are current drought conditions compared
              to what&rsquo;s typical in this area?&quot;
            </i>
          </p>
          <p>
            For example, if an area is classified under{" "}
            <b>Severe Drought (D2)</b>, it means that in the long-term record
            (usually 40+ years),{" "}
            <b>conditions have only been this dry less than 10% of the time</b>.
            This percentile-based method allows us to detect both long-term
            droughts and short-lived, extreme events—always in the context of
            local climate norms.
          </p>
          <table className="w-full border border-gray-300">
            <thead>
              <tr className="bg-gray-100">
                <th className="border border-gray-300 text-left font-semibold p-2">
                  Category
                </th>
                <th className="border border-gray-300 text-left font-semibold p-2">
                  Description
                </th>
                <th className="border border-gray-300 text-left font-semibold p-2">
                  CDI Percentile
                </th>
                <th className="border border-gray-300 text-left font-semibold p-2">
                  Meaning
                </th>
              </tr>
            </thead>
            <tbody>
              {[
                {
                  category: "None",
                  description: "Normal or wet",
                  percentile: ">30.01",
                  meaning: "Common or wetter-than-average",
                  color: DROUGHT_CATEGORY_COLOR[DROUGHT_CATEGORY_VALUE.normal],
                },
                {
                  category: "D0",
                  description: "Abnormally Dry",
                  percentile: "20.01 – 30.00",
                  meaning: "Drier than usual, but not yet drought",
                  color: DROUGHT_CATEGORY_COLOR[DROUGHT_CATEGORY_VALUE.d0],
                },
                {
                  category: "D1",
                  description: "Moderate Drought",
                  percentile: "10.01 – 20.00",
                  meaning: "Unusual dryness—seen ~1 in 5 years",
                  color: DROUGHT_CATEGORY_COLOR[DROUGHT_CATEGORY_VALUE.d1],
                },
                {
                  category: "D2",
                  description: "Severe Drought",
                  percentile: "5.01 – 10.00",
                  meaning: "Rarely this dry—<10% of the time",
                  color: DROUGHT_CATEGORY_COLOR[DROUGHT_CATEGORY_VALUE.d2],
                },
                {
                  category: "D3",
                  description: "Extreme Drought",
                  percentile: "2.01 – 5.00",
                  meaning: "Extreme dryness—only ~2–5% of years",
                  color: DROUGHT_CATEGORY_COLOR[DROUGHT_CATEGORY_VALUE.d3],
                },
                {
                  category: "D4",
                  description: "Exceptional Drought",
                  percentile: "0.00 – 2.00",
                  meaning: "Among the driest conditions on record",
                  color: DROUGHT_CATEGORY_COLOR[DROUGHT_CATEGORY_VALUE.d4],
                },
              ].map((row, index) => (
                <tr className="edh-row" key={index}>
                  <td
                    className={`border border-gray-300 p-2 bg-[${row.color}]`}
                  >
                    {row.category}
                  </td>
                  <td className="border border-gray-300 p-2">
                    {row.description}
                  </td>
                  <td className="border border-gray-300 p-2">
                    {row.percentile}
                  </td>
                  <td className="border border-gray-300 p-2">{row.meaning}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <h2 className="text-xl font-semibold text-gray-800 pt-4">
          Who is Involved in Validation?
        </h2>
        <div className="text-gray-700 pb-12 space-y-4">
          <p>
            The <b>Technical Working Group (TWG)</b>—comprising representatives
            from Eswatini’s NDMA, the Ministry of Agriculture, MET, Department
            of Water Affairs (DWA) and the University of Eswatini (UNESWA)
            —plays a crucial role in the review and validation process.
          </p>
          <div className="w-full">
            <p>Their responsibilities include:</p>
            <ul className="list-disc list-inside pl-4 leading-8">
              <li>Reviewing the generated maps monthly.</li>
              <li>Benchmarking against other datasets and ground reports.</li>
              <li>Approving or requesting changes before publication.</li>
            </ul>
          </div>
        </div>
      </div>
      <LogoSection />
      <FeedbackSection />
    </div>
  );
};

export default AboutPage;
