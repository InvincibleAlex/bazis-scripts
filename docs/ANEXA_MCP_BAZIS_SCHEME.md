# Anexă — schemele MCP BAZIS expuse în sesiunea de origine

Data: 26.11.2026. Citește schema efectivă din chatul de pe RG înainte de apelare; această anexă nu instalează instrumentele.

## bazis_capabilities

```ts
declare const tools: { mcp__bazis__bazis_capabilities(args: { [key: string]: unknown; }): Promise<CallToolResult<{ [key: string]: unknown; }>>; };
```

## bazis_create_cabinet

```ts
declare const tools: { mcp__bazis__bazis_create_cabinet(args: { back_material?: string | null; back_thickness?: number; depth: number; height: number; material?: string | null; model_token: string; name: string; shelves?: number; thickness?: number; width: number; x?: number; y?: number; z?: number; }): Promise<CallToolResult<{ [key: string]: unknown; }>>; };
```

## bazis_create_panel

```ts
declare const tools: { mcp__bazis__bazis_create_panel(args: { height: number; material?: string | null; model_token: string; name: string; orientation: "front" | "horizontal" | "vertical"; thickness: number; width: number; x?: number; y?: number; z?: number; }): Promise<CallToolResult<{ [key: string]: unknown; }>>; };
```

## bazis_delete_objects

```ts
declare const tools: { mcp__bazis__bazis_delete_objects(args: { model_token: string; object_ids: Array<string>; }): Promise<CallToolResult<{ [key: string]: unknown; }>>; };
```

## bazis_duplicate_objects

```ts
declare const tools: { mcp__bazis__bazis_duplicate_objects(args: { dx?: number; dy?: number; dz?: number; model_token: string; object_ids: Array<string>; }): Promise<CallToolResult<{ [key: string]: unknown; }>>; };
```

## bazis_get_model

```ts
declare const tools: { mcp__bazis__bazis_get_model(args: { [key: string]: unknown; }): Promise<CallToolResult<{ [key: string]: unknown; }>>; };
```

## bazis_get_object

```ts
declare const tools: { mcp__bazis__bazis_get_object(args: { object_id: string; }): Promise<CallToolResult<{ [key: string]: unknown; }>>; };
```

## bazis_get_selection

```ts
declare const tools: { mcp__bazis__bazis_get_selection(args: { [key: string]: unknown; }): Promise<CallToolResult<{ [key: string]: unknown; }>>; };
```

## bazis_list_objects

```ts
declare const tools: { mcp__bazis__bazis_list_objects(args: { limit?: number; name_contains?: string; offset?: number; parent_id?: string | null; recursive?: boolean; }): Promise<CallToolResult<{ [key: string]: unknown; }>>; };
```

## bazis_move_objects

```ts
declare const tools: { mcp__bazis__bazis_move_objects(args: { dx?: number; dy?: number; dz?: number; model_token: string; object_ids: Array<string>; }): Promise<CallToolResult<{ [key: string]: unknown; }>>; };
```

## bazis_ping

```ts
declare const tools: { mcp__bazis__bazis_ping(args: { [key: string]: unknown; }): Promise<CallToolResult<{ [key: string]: unknown; }>>; };
```

## bazis_request_result

```ts
declare const tools: { mcp__bazis__bazis_request_result(args: { request_id: string; }): Promise<CallToolResult<{ [key: string]: unknown; }>>; };
```

## bazis_rotate_objects

```ts
declare const tools: { mcp__bazis__bazis_rotate_objects(args: { angle: number; axis: "x" | "y" | "z"; model_token: string; object_ids: Array<string>; }): Promise<CallToolResult<{ [key: string]: unknown; }>>; };
```

## bazis_save_model_copy

```ts
declare const tools: { mcp__bazis__bazis_save_model_copy(args: { filename: string; model_token: string; }): Promise<CallToolResult<{ [key: string]: unknown; }>>; };
```

## bazis_select_objects

```ts
declare const tools: { mcp__bazis__bazis_select_objects(args: { model_token: string; object_ids: Array<string>; replace?: boolean; }): Promise<CallToolResult<{ [key: string]: unknown; }>>; };
```

## bazis_set_properties

```ts
declare const tools: { mcp__bazis__bazis_set_properties(args: { art_pos?: string | null; designation?: string | null; model_token: string; name?: string | null; object_ids: Array<string>; visible?: boolean | null; }): Promise<CallToolResult<{ [key: string]: unknown; }>>; };
```

## bazis_set_view

```ts
declare const tools: { mcp__bazis__bazis_set_view(args: { fit_all?: boolean; view?: "front" | "back" | "left" | "right" | "top" | "bottom" | "isometric"; }): Promise<CallToolResult<{ [key: string]: unknown; }>>; };
```

## bazis_settings_apply

```ts
declare const tools: { mcp__bazis__bazis_settings_apply(args: { stage_id: string; }): Promise<CallToolResult<{ [key: string]: unknown; }>>; };
```

## bazis_settings_catalog

```ts
declare const tools: { mcp__bazis__bazis_settings_catalog(args: { [key: string]: unknown; }): Promise<CallToolResult<{ [key: string]: unknown; }>>; };
```

## bazis_settings_read

```ts
declare const tools: { mcp__bazis__bazis_settings_read(args: { file_id: string; limit?: number; offset?: number; query?: string; }): Promise<CallToolResult<{ [key: string]: unknown; }>>; };
```

## bazis_settings_restore

```ts
declare const tools: { mcp__bazis__bazis_settings_restore(args: { stage_id: string; }): Promise<CallToolResult<{ [key: string]: unknown; }>>; };
```

## bazis_settings_result

```ts
declare const tools: { mcp__bazis__bazis_settings_result(args: { stage_id: string; }): Promise<CallToolResult<{ [key: string]: unknown; }>>; };
```

## bazis_settings_stage

```ts
declare const tools: { mcp__bazis__bazis_settings_stage(args: { changes: Array<{ expected_value: string; setting_id: string; value: string | boolean | number | number; }>; expected_revision: string; file_id: string; }): Promise<CallToolResult<{ [key: string]: unknown; }>>; };
```

## bazis_status

```ts
declare const tools: { mcp__bazis__bazis_status(args: { [key: string]: unknown; }): Promise<CallToolResult<{ [key: string]: unknown; }>>; };
```

## bazis_stop_bridge

```ts
declare const tools: { mcp__bazis__bazis_stop_bridge(args: { [key: string]: unknown; }): Promise<CallToolResult<{ [key: string]: unknown; }>>; };
```

