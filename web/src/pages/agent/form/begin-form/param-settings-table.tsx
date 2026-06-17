'use client';

import {
  ColumnDef,
  ColumnFiltersState,
  SortingState,
  VisibilityState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table';
import { Pencil, Trash2 } from 'lucide-react';
import * as React from 'react';

import { TableEmpty } from '@/components/table-skeleton';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { ParamSetting } from '../../interface';

interface IProps {
  data: ParamSetting[];
  deleteRecord(index: number): void;
  showModal(index: number, record: ParamSetting): void;
}

export function ParamSettingsTable({
  data = [],
  deleteRecord,
  showModal,
}: IProps) {
  const [sorting, setSorting] = React.useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>(
    [],
  );
  const [columnVisibility, setColumnVisibility] =
    React.useState<VisibilityState>({});

  const columns: ColumnDef<ParamSetting>[] = [
    {
      accessorKey: 'name_cn',
      header: '参数中文名称',
      meta: { cellClassName: 'max-w-30' },
      cell: ({ row }) => {
        const name: string = row.getValue('name_cn');
        return (
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="truncate">{name}</div>
            </TooltipTrigger>
            <TooltipContent>
              <p>{name}</p>
            </TooltipContent>
          </Tooltip>
        );
      },
    },
    {
      accessorKey: 'name_en',
      header: '参数英文名称',
      meta: { cellClassName: 'max-w-30' },
      cell: ({ row }) => {
        const name: string = row.getValue('name_en');
        return (
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="truncate">{name}</div>
            </TooltipTrigger>
            <TooltipContent>
              <p>{name}</p>
            </TooltipContent>
          </Tooltip>
        );
      },
    },
    {
      accessorKey: 'default_value',
      header: '参数默认值',
      meta: { cellClassName: 'max-w-30' },
      cell: ({ row }) => {
        const val: string = row.getValue('default_value');
        return (
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="truncate">{val}</div>
            </TooltipTrigger>
            <TooltipContent>
              <p>{val}</p>
            </TooltipContent>
          </Tooltip>
        );
      },
    },
    {
      accessorKey: 'param_type',
      header: '参数类型',
      cell: ({ row }) => {
        const paramType: string = row.getValue('param_type');
        return <div>{paramType === 'string' ? '字符串' : '文件'}</div>;
      },
    },
    {
      id: 'actions',
      enableHiding: false,
      header: '操作',
      cell: ({ row }) => {
        const record = row.original;
        const idx = row.index;

        return (
          <div>
            <Button
              className="bg-transparent text-foreground hover:bg-muted-foreground hover:text-foreground"
              onClick={() => showModal(idx, record)}
            >
              <Pencil />
            </Button>
            <Button
              className="bg-transparent text-foreground hover:bg-muted-foreground hover:text-foreground"
              onClick={() => deleteRecord(idx)}
            >
              <Trash2 />
            </Button>
          </div>
        );
      },
    },
  ];

  const table = useReactTable({
    data,
    columns,
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    onColumnVisibilityChange: setColumnVisibility,
    state: {
      sorting,
      columnFilters,
      columnVisibility,
    },
  });

  return (
    <div className="rounded-md border w-full bg-bg-card">
      <Table rootClassName="rounded-md">
        <TableHeader className="bg-bg-card">
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id}>
              {headerGroup.headers.map((header) => {
                return (
                  <TableHead key={header.id}>
                    {header.isPlaceholder
                      ? null
                      : flexRender(
                          header.column.columnDef.header,
                          header.getContext(),
                        )}
                  </TableHead>
                );
              })}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {table.getRowModel().rows?.length ? (
            table.getRowModel().rows.map((row) => (
              <TableRow
                key={row.id}
                data-state={row.getIsSelected() && 'selected'}
              >
                {row.getVisibleCells().map((cell) => (
                  <TableCell
                    key={cell.id}
                    className={cn(cell.column.columnDef.meta?.cellClassName)}
                  >
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                ))}
              </TableRow>
            ))
          ) : (
            <TableEmpty columnsLength={columns.length}></TableEmpty>
          )}
        </TableBody>
      </Table>
    </div>
  );
}
