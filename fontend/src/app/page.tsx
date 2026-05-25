"use client";

import { useQuery } from "@tanstack/react-query";
import { indicatorService, countryService } from "@/services/data-service";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { useState } from "react";

export default function Dashboard() {
  const [selectedCountry, setSelectedCountry] = useState("VNM");

  const { data: countries } = useQuery({
    queryKey: ["countries"],
    queryFn: countryService.list,
  });

  const { data: gdpData, isLoading } = useQuery({
    queryKey: ["indicators", selectedCountry, "NY.GDP.MKTP.CD"],
    queryFn: () => indicatorService.query({ country_code: selectedCountry }),
  });

  return (
    <div className="p-6 flex flex-col gap-6">
      <header className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold">Kinh tế vĩ mô</h2>
          <p className="text-zinc-500 text-sm">Tổng quan các chỉ số GDP và tăng trưởng</p>
        </div>
        <select
          className="bg-white border border-zinc-200 rounded-md px-3 py-1.5 text-sm"
          value={selectedCountry}
          onChange={(e) => setSelectedCountry(e.target.value)}
        >
          {countries?.map((c) => (
            <option key={c.country_code} value={c.country_code}>
              {c.country_name}
            </option>
          ))}
        </select>
      </header>

      <div className="bg-white p-6 rounded-xl border border-zinc-200 shadow-sm">
        <h3 className="font-semibold mb-6">Biến động GDP qua các năm</h3>
        <div className="h-[400px] w-full">
          {isLoading ? (
            <div className="h-full w-full flex items-center justify-center bg-zinc-50 rounded">
              Đang tải dữ liệu...
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={gdpData?.sort((a, b) => a.year - b.year)}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="year" fontSize={12} />
                <YAxis
                  fontSize={12}
                  tickFormatter={(val) => `$${(val / 1e9).toFixed(0)}B`}
                />
                <Tooltip
                  formatter={(val: any) => [
                    `$${(Number(val) / 1e9).toFixed(2)} Billion`,
                    "GDP",
                  ]}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="value"
                  name="GDP (Current US$)"
                  stroke="#18181b"
                  strokeWidth={2}
                  dot={{ r: 4 }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </div>
  );
}
