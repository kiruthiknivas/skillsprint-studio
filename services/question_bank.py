import random
from typing import List, Dict, Any

# Curated library of real-world interview questions organized by topic and difficulty
QUESTIONS_DATA = {
    ".NET": [
        {
            "question": "In ASP.NET Core, what is the key difference between AddScoped and AddTransient service lifetimes?",
            "code_snippet": "builder.Services.AddScoped<IOrderService, OrderService>();\nbuilder.Services.AddTransient<ITaxCalculator, TaxCalculator>();",
            "options": [
                "A) AddScoped creates an instance per HTTP request; AddTransient creates a new instance every time it is requested.",
                "B) AddScoped is a singleton per process; AddTransient is scoped to the current thread.",
                "C) AddScoped creates instances only for controllers; AddTransient is for background workers.",
                "D) AddScoped is deprecated in .NET 8 in favor of AddTransient."
            ],
            "correct_answer": "A",
            "hint": "Think about the lifecycle of an incoming web request and whether sub-services within that same request should share the same stateful instance (like an Entity Framework DbContext).",
            "explanation": "AddScoped registers a service whose instance is created once per HTTP request and shared across all dependencies injected within that same request scope. AddTransient creates a fresh instance every single time the container resolves the dependency. Entity Framework's DbContext is registered as Scoped so that a single unit-of-work is maintained per request.",
            "difficulty": "Intermediate",
            "topic": ".NET Core / C#"
        },
        {
            "question": "What is the primary difference between Task.Run and async/await for I/O-bound operations in .NET?",
            "code_snippet": "// Approach A:\nawait httpClient.GetStringAsync(url);\n\n// Approach B:\nawait Task.Run(() => httpClient.GetStringAsync(url));",
            "options": [
                "A) Approach A uses asynchronous I/O completion ports without blocking a thread pool thread, whereas Approach B wastes a thread pool thread.",
                "B) Approach B executes faster because Task.Run spawns a dedicated CPU thread.",
                "C) There is no difference; both consume one active worker thread throughout the duration of the network call.",
                "D) Approach A will deadlock unless ConfigureAwait(false) is called."
            ],
            "correct_answer": "A",
            "hint": "Does an I/O operation like downloading a web page or reading from disk need CPU execution while waiting for the packets to arrive over the wire?",
            "explanation": "Pure I/O operations (like HTTP requests, DB queries) rely on hardware DMA and OS completion ports (IOCP in Windows). No CPU thread is actively needed while waiting. Wrapping an I/O call in Task.Run needlessly consumes a ThreadPool thread just to start waiting, reducing application throughput.",
            "difficulty": "Intermediate",
            "topic": ".NET Core / C#"
        },
        {
            "question": "What does the `record` type provide in C# 9+ compared to a standard `class`?",
            "code_snippet": "public record UserDto(int Id, string Name, string Email);",
            "options": [
                "A) Built-in value-based equality, non-destructive mutation (`with` expression), and concise syntax for immutable data models.",
                "B) Records are always allocated on the stack like structs to eliminate garbage collection.",
                "C) Records cannot have methods or properties and only store primitive values.",
                "D) Records are automatically synchronized across multiple threads without locks."
            ],
            "correct_answer": "A",
            "hint": "Think about comparing two DTO instances with identical property values. What does Equals() return for a record vs a regular class?",
            "explanation": "Records in C# synthesize value-based equality (two record instances with identical property values are equal), a deconstructor, custom ToString(), and support non-destructive cloning via the `with` expression. By default, positional record classes are reference types with immutable properties.",
            "difficulty": "Intermediate",
            "topic": ".NET Core / C#"
        },
        {
            "question": "What is the consequence of executing a LINQ query with `.AsNoTracking()` in Entity Framework Core?",
            "code_snippet": "var products = await dbContext.Products\n    .AsNoTracking()\n    .Where(p => p.IsActive)\n    .ToListAsync();",
            "options": [
                "A) EF Core does not track entities in the ChangeTracker, significantly improving read performance and reducing memory overhead.",
                "B) The query executes without acquiring database locks, risking dirty reads.",
                "C) The entities cannot be displayed in UI components or serialized to JSON.",
                "D) EF Core will automatically execute the query asynchronously on a secondary database replica."
            ],
            "correct_answer": "A",
            "hint": "When you only need to return data to an API response and won't call SaveChanges() on those entities, does EF Core need to keep snapshot copies of them?",
            "explanation": "When EF Core tracks entities, it creates snapshot copies in its ChangeTracker to detect modifications. For read-only operations (like GET endpoints in Web APIs), using .AsNoTracking() bypasses snapshot creation and identity resolution, providing notable speed and memory gains.",
            "difficulty": "Intermediate",
            "topic": ".NET Core / C#"
        },
        {
            "question": "How does ASP.NET Core Middleware pipeline process an incoming HTTP request?",
            "code_snippet": "app.UseAuthentication();\napp.UseAuthorization();\napp.UseResponseCaching();",
            "options": [
                "A) Middlewares are executed in the exact order they are registered for requests, and in reverse order for outgoing responses (Russian doll / pipeline model).",
                "B) Middlewares execute in arbitrary parallel threads based on available CPU cores.",
                "C) Middlewares only process outgoing responses, not incoming requests.",
                "D) The order of `app.Use...` does not matter because ASP.NET Core reorders them automatically based on attributes."
            ],
            "correct_answer": "A",
            "hint": "If UseAuthorization() is placed BEFORE UseAuthentication(), how would the app know who the user is when checking permissions?",
            "explanation": "ASP.NET Core middlewares form a bi-directional pipeline. A request flows through middlewares in the order configured in Program.cs. When `next()` is called, control passes forward. Once downstream middlewares finish, the response travels backward through the same middlewares in reverse order.",
            "difficulty": "Beginner",
            "topic": ".NET Core / C#"
        },
        {
            "question": "What happens if an unhandled exception is thrown inside an `async void` method in C#?",
            "code_snippet": "public async void ProcessPaymentAsync()\n{\n    throw new InvalidOperationException(\"Payment gateway timeout\");\n}",
            "options": [
                "A) The exception cannot be caught by a caller's try/catch block and crashes the process or gets raised on the SynchronizationContext.",
                "B) The exception is automatically wrapped inside an AggregateException and handled silently.",
                "C) The compiler gives a build error because async methods must return Task or Task<T>.",
                "D) It returns null to the caller and writes a warning to the console."
            ],
            "correct_answer": "A",
            "hint": "`async void` should only ever be used for event handlers. Why can't a caller await an `async void` method?",
            "explanation": "Because `async void` does not return a `Task`, callers cannot await it or wrap the call in a `try/catch` block. Any unhandled exception is posted directly to the current SynchronizationContext, which in ASP.NET Core or console apps typically terminates the worker process. Always return `Task` instead of `void` for async methods.",
            "difficulty": "Harder",
            "topic": ".NET Core / C#"
        },
        {
            "question": "In C#, what is the difference between `IEnumerable<T>` and `IQueryable<T>`?",
            "code_snippet": "IEnumerable<Customer> q1 = db.Customers.Where(c => c.City == \"Dallas\");\nIQueryable<Customer> q2 = db.Customers.Where(c => c.City == \"Dallas\");",
            "options": [
                "A) IQueryable converts expressions to SQL and executes filtering on the database server; IEnumerable executes in-memory after loading records into client memory.",
                "B) IEnumerable is for SQL Server; IQueryable is for NoSQL databases.",
                "C) IEnumerable supports pagination; IQueryable only supports full table scans.",
                "D) There is no performance difference; IQueryable is simply an interface alias for IEnumerable."
            ],
            "correct_answer": "A",
            "hint": "IQueryable has an `Expression` tree that LINQ providers can translate into SQL before querying the database.",
            "explanation": "IQueryable<T> uses Expression Trees, allowing ORMs like EF Core to translate LINQ operators (Where, Select, Take) into native SQL statements executed on the DB server. IEnumerable<T> works in-memory using delegates (Func), meaning calling Where on an IEnumerable loaded from a DB table will fetch all rows into RAM and filter client-side.",
            "difficulty": "Intermediate",
            "topic": ".NET Core / C#"
        },
        {
            "question": "What does the `yield return` statement do in a C# method?",
            "code_snippet": "public IEnumerable<int> GetNumbers()\n{\n    yield return 1;\n    yield return 2;\n    yield return 3;\n}",
            "options": [
                "A) It implements deferred / lazy execution, returning items one at a time on-demand as the caller enumerates.",
                "B) It releases CPU execution to other threads like Thread.Yield().",
                "C) It converts the return value into a parallel observable stream.",
                "D) It creates an immutable array containing all returned items immediately."
            ],
            "correct_answer": "A",
            "hint": "When you call `GetNumbers()`, does it compute all items upfront or only when `MoveNext()` is called on the enumerator?",
            "explanation": "`yield return` causes the compiler to generate a state machine implementing IEnumerator<T>. The method executes lazily: it pauses execution at each `yield return` and resumes only when the consumer requests the next item (e.g. in a foreach loop), saving significant memory when dealing with large collections.",
            "difficulty": "Beginner",
            "topic": ".NET Core / C#"
        },
        {
            "question": "In ASP.NET Core, what is the role of `IOptionsSnapshot<T>` vs `IOptions<T>`?",
            "code_snippet": "public class OrderService\n{\n    public OrderService(IOptionsSnapshot<PaymentSettings> settings)\n    { ... }\n}",
            "options": [
                "A) IOptionsSnapshot reloads configuration values per HTTP request when appsettings.json changes; IOptions is a singleton and never reloads after startup.",
                "B) IOptionsSnapshot is for testing mocks; IOptions is for production.",
                "C) IOptionsSnapshot encrypts connection strings; IOptions stores them in plain text.",
                "D) IOptionsSnapshot is only compatible with Azure Key Vault."
            ],
            "correct_answer": "A",
            "hint": "If an administrator updates appsettings.json while the API is running in production, which pattern detects the change without restarting the app?",
            "explanation": "IOptions<T> is registered as a Singleton and reads options once when initialized. IOptionsSnapshot<T> is Scoped and re-evaluates configuration per request, making it ideal when configuration sources reload dynamically without restarting the application. For Singletons requiring reload notifications, `IOptionsMonitor<T>` is used.",
            "difficulty": "Intermediate",
            "topic": ".NET Core / C#"
        },
        {
            "question": "What is the primary benefit of using `Span<T>` and `Memory<T>` in modern .NET?",
            "code_snippet": "ReadOnlySpan<char> slice = str.AsSpan(0, 10);",
            "options": [
                "A) Zero-allocation slicing and memory manipulation over contiguous memory buffers without creating new heap objects.",
                "B) Automatic distributed caching across server nodes.",
                "C) Hardware GPU acceleration for math calculations.",
                "D) Making string manipulations thread-safe without locks."
            ],
            "correct_answer": "A",
            "hint": "When slicing a string using `str.Substring()`, a new string is allocated on the heap. What does `AsSpan()` allocate?",
            "explanation": "`Span<T>` is a ref struct representing a contiguous region of arbitrary memory (stack, managed heap, or unmanaged). It allows high-performance parsing and slicing without heap allocations or GC pressure. `Memory<T>` is its heap-safe counterpart that can outlive the current stack frame and be used across async boundaries.",
            "difficulty": "Harder",
            "topic": ".NET Core / C#"
        }
    ],

    "Angular": [
        {
            "question": "What is the difference between `@Component({ changeDetection: ChangeDetectionStrategy.OnPush })` and the default ChangeDetectionStrategy in Angular?",
            "code_snippet": "@Component({\n  selector: 'app-user-profile',\n  changeDetection: ChangeDetectionStrategy.OnPush,\n  templateUrl: './user-profile.component.html'\n})\nexport class UserProfileComponent { ... }",
            "options": [
                "A) OnPush only triggers change detection when an @Input reference changes, an event originated inside the component, or an observable piped with `async` emits.",
                "B) OnPush disables change detection completely for this component and all its children permanently.",
                "C) OnPush forces change detection to run on a background web worker thread.",
                "D) OnPush is only compatible with Angular template forms, not Reactive forms."
            ],
            "correct_answer": "A",
            "hint": "In default change detection, Zone.js checks every component on the tree whenever ANY browser event or timer fires. How does OnPush optimize this?",
            "explanation": "With `Default` change detection, Angular traverses the entire component tree on any macro/microtask (clicks, HTTP responses, setTimeout). With `OnPush`, Angular skips checking the component unless an `@Input()` reference changes (using `===` identity), a DOM event originated inside the component, or the template triggers markForCheck() (like the `async` pipe or Signals). This vastly improves performance in large apps.",
            "difficulty": "Intermediate",
            "topic": "Angular & TypeScript"
        },
        {
            "question": "In Angular (v16+), what is a `Signal` and how does it compare to an RxJS `Observable`?",
            "code_snippet": "count = signal(0);\ndoubleCount = computed(() => this.count() * 2);\n\nincrement() {\n  this.count.update(c => c + 1);\n}",
            "options": [
                "A) Signals are synchronous, glitch-free reactive state primitives that track dependencies automatically without requiring manual unsubscription.",
                "B) Signals replace all HTTP requests and WebSocket connections in Angular.",
                "C) Signals are only for styling and animations.",
                "D) Signals require an active Zone.js instance to propagate changes to the DOM."
            ],
            "correct_answer": "A",
            "hint": "Unlike Observables which emit asynchronous streams of values over time and need subscription management, how do you read a Signal's current value?",
            "explanation": "Angular Signals provide fine-grained reactivity. They always hold a synchronous current value, track consumers and dependencies automatically, and notify Angular's template compiler precisely which DOM node needs updating. Unlike Observables, Signals don't have subscription lifecycle leaks in templates, while RxJS remains best for asynchronous events, debounce, and HTTP retry logic.",
            "difficulty": "Intermediate",
            "topic": "Angular & TypeScript"
        },
        {
            "question": "What is the key difference between `switchMap` and `mergeMap` in RxJS?",
            "code_snippet": "this.searchControl.valueChanges.pipe(\n  debounceTime(300),\n  switchMap(query => this.apiService.search(query))\n).subscribe(results => this.results = results);",
            "options": [
                "A) `switchMap` cancels the previous inner observable when a new value arrives; `mergeMap` runs all inner observables concurrently without cancelling.",
                "B) `switchMap` concatenates observables sequentially; `mergeMap` ignores new values until the first completes.",
                "C) `switchMap` is only for GET requests; `mergeMap` is only for POST requests.",
                "D) There is no difference; they are aliases in RxJS 7+."
            ],
            "correct_answer": "A",
            "hint": "In a live search autocomplete box, if the user types 'A' and then quickly types 'AB', what should happen to the HTTP request searching for 'A'?",
            "explanation": "`switchMap` unsubscribes (cancels) the previous pending inner observable whenever a new value emits from the source. This prevents race conditions in search inputs where an older, slower request might overwrite newer search results. `mergeMap` handles all inner observables concurrently without cancellation.",
            "difficulty": "Intermediate",
            "topic": "Angular & TypeScript"
        },
        {
            "question": "Why is it important to unsubscribe from RxJS Observables in Angular components, and what is the cleanest modern way to do so?",
            "code_snippet": "export class DashboardComponent {\n  private destroyRef = inject(DestroyRef);\n\n  ngOnInit() {\n    this.dataService.stream$\n      .pipe(takeUntilDestroyed(this.destroyRef))\n      .subscribe(data => this.data = data);\n  }\n}",
            "options": [
                "A) Unsubscribing prevents memory leaks caused by lingering references; `takeUntilDestroyed()` automatically completes the subscription when the component is destroyed.",
                "B) Observables crash the browser if left open for more than 5 minutes.",
                "C) Unsubscribing frees server RAM on the backend web server.",
                "D) Angular components unsubscribe automatically from all subscriptions without any code."
            ],
            "correct_answer": "A",
            "hint": "If a long-lived service holds a subscription to a component that was navigated away from, the component instance cannot be garbage-collected.",
            "explanation": "Long-lived observables (like event streams, router events, or singleton service subjects) retain references to component callbacks. If not unsubscribed, the destroyed component remains in memory (a memory leak). `takeUntilDestroyed` (introduced in modern Angular) ties stream completion directly to the component's `DestroyRef` injection token, eliminating manual ngOnDestroy boilerplate.",
            "difficulty": "Intermediate",
            "topic": "Angular & TypeScript"
        },
        {
            "question": "What is an Angular HTTP Interceptor and what is its primary use case?",
            "code_snippet": "export const authInterceptor: HttpInterceptorFn = (req, next) => {\n  const token = inject(AuthService).getToken();\n  const authReq = req.clone({\n    setHeaders: { Authorization: `Bearer ${token}` }\n  });\n  return next(authReq);\n};",
            "options": [
                "A) A middleware mechanism to inspect, transform, or handle all outgoing HTTP requests and incoming HTTP responses globally (e.g. injecting JWT tokens, handling 401s).",
                "B) A firewall plugin that blocks unauthorized external scripts from loading.",
                "C) A service worker that caches images locally in IndexedDB.",
                "D) A tool to compile Angular TypeScript code into WebAssembly."
            ],
            "correct_answer": "A",
            "hint": "Instead of adding `headers: { Authorization: ... }` manually in every single service method, where can you centralize request modifications?",
            "explanation": "HttpInterceptors sit between your application and the backend. They provide a centralized location to attach authentication headers, log API latency, retry failed network requests, or catch global HTTP errors (like redirecting to /login on 401 Unauthorized responses).",
            "difficulty": "Beginner",
            "topic": "Angular & TypeScript"
        },
        {
            "question": "In Angular, what is the difference between Standalone Components and NgModule-based components?",
            "code_snippet": "@Component({\n  selector: 'app-card',\n  standalone: true,\n  imports: [CommonModule, RouterModule],\n  template: `<div>Card Content</div>`\n})\nexport class CardComponent {}",
            "options": [
                "A) Standalone components manage their own dependencies directly in the `imports` array without needing declaration inside an `@NgModule`.",
                "B) Standalone components cannot use dependency injection or routing.",
                "C) Standalone components are compiled at runtime (JIT) only, whereas NgModules use Ahead-of-Time (AOT).",
                "D) Standalone components can only be used in Angular Universal (SSR)."
            ],
            "correct_answer": "A",
            "hint": "Introduced in Angular 14 and default in Angular 17+, how do standalone components simplify project architecture?",
            "explanation": "Standalone components remove the boilerplate of `@NgModule`. A standalone component declares its own direct imports (`imports: [CommonModule, MatButtonModule]`), making components self-contained, easier to lazy-load, simpler for unit testing, and friendlier to tree-shaking.",
            "difficulty": "Beginner",
            "topic": "Angular & TypeScript"
        },
        {
            "question": "What is the purpose of Angular Route Guards like `canActivate` and `canDeactivate`?",
            "code_snippet": "export const authGuard: CanActivateFn = (route, state) => {\n  const authService = inject(AuthService);\n  const router = inject(Router);\n  return authService.isLoggedIn() ? true : router.parseUrl('/login');\n};",
            "options": [
                "A) `canActivate` controls access to a route based on conditions (e.g. auth); `canDeactivate` prompts the user before navigating away (e.g. unsaved form changes).",
                "B) Route guards encrypt route parameters in the browser history.",
                "C) Route guards prevent cross-site scripting (XSS) attacks in HTML templates.",
                "D) Route guards preload all lazy-loaded chunks in the background."
            ],
            "correct_answer": "A",
            "hint": "Think about protecting an /admin dashboard from unauthenticated users, or warning a user who has unsaved work in a form.",
            "explanation": "Route Guards are interfaces or functional guards (`CanActivateFn`, `CanDeactivateFn`) that dictate navigation flow. `canActivate` checks permissions before navigating to a route; `canDeactivate` checks whether the user can leave the current route (e.g., displaying a 'You have unsaved changes' modal).",
            "difficulty": "Beginner",
            "topic": "Angular & TypeScript"
        },
        {
            "question": "In TypeScript, what is the difference between `interface` and `type` alias?",
            "code_snippet": "interface IUser { id: number; name: string; }\ntype UserType = { id: number; name: string; };",
            "options": [
                "A) Interfaces support declaration merging and OOP inheritance (`extends`); `type` aliases can represent unions, primitives, and mapped types.",
                "B) Interfaces exist at runtime in JavaScript; `type` aliases are removed during compilation.",
                "C) `type` aliases cannot define object properties, only primitive numbers and strings.",
                "D) Interfaces are slower to compile than `type` aliases."
            ],
            "correct_answer": "A",
            "hint": "Can you declare the same `interface` name twice across files and have TypeScript combine their fields?",
            "explanation": "Interfaces are open for declaration merging (ideal for library authors extending existing types) and object-oriented polymorphism. `type` aliases are more flexible for functional programming as they can define union types (`string | number`), tuple types, intersection types, and conditional types.",
            "difficulty": "Intermediate",
            "topic": "Angular & TypeScript"
        },
        {
            "question": "What is the difference between `@ViewChild` with `{ static: true }` vs `{ static: false }`?",
            "code_snippet": "@ViewChild('inputRef', { static: false }) inputElement!: ElementRef;",
            "options": [
                "A) `{ static: true }` resolves the element before change detection in `ngOnInit`; `{ static: false }` resolves after change detection in `ngAfterViewInit` (necessary if inside `*ngIf`).",
                "B) `{ static: true }` makes the element immutable and prevents DOM events from firing.",
                "C) `{ static: false }` clones the element into a Shadow DOM boundary.",
                "D) Static setting has been removed and is ignored in all Angular versions."
            ],
            "correct_answer": "A",
            "hint": "If an element is wrapped inside an `*ngIf` structural directive, can Angular find it before change detection runs?",
            "explanation": "If a template query result is needed in `ngOnInit()`, `{ static: true }` is used, but the element must NOT be inside a dynamic template block (like `*ngIf` or `*ngFor`). If the element depends on dynamic bindings, `{ static: false }` resolves the reference in `ngAfterViewInit()`.",
            "difficulty": "Harder",
            "topic": "Angular & TypeScript"
        },
        {
            "question": "How does Angular's dependency injection hierarchy resolve services registered in a Component's `providers: [...]` vs `providedIn: 'root'`?",
            "code_snippet": "@Component({\n  selector: 'app-editor',\n  providers: [EditorStateService] // Component-level provider\n})\nexport class EditorComponent {}",
            "options": [
                "A) Component-level providers create a new private service instance for each instance of that component; `providedIn: 'root'` is a singleton shared app-wide.",
                "B) Component providers are destroyed immediately after `ngOnInit`.",
                "C) `providedIn: 'root'` creates a new instance on every HTTP route change.",
                "D) Component providers can only be injected into child templates, not child TypeScript components."
            ],
            "correct_answer": "A",
            "hint": "If you have two `app-editor` instances on the screen, should they share the exact same draft text or have independent state?",
            "explanation": "Angular uses a hierarchical injector tree. Services with `providedIn: 'root'` are singletons at the application root level. When a service is provided in a Component's `providers` array, Angular creates an injector node tied to that component's lifecycle: each component instance gets its own isolated service instance which is automatically garbage collected when that component is destroyed.",
            "difficulty": "Intermediate",
            "topic": "Angular & TypeScript"
        }
    ],

    "SQL Server": [
        {
            "question": "What is the fundamental architectural difference between a Clustered Index and a Non-Clustered Index in SQL Server?",
            "code_snippet": "CREATE CLUSTERED INDEX IX_Orders_OrderDate ON Orders(OrderDate);\nCREATE NONCLUSTERED INDEX IX_Orders_CustomerID ON Orders(CustomerID);",
            "options": [
                "A) A Clustered Index defines the physical sort order of the table's actual data pages (leaf level is the data); a Non-Clustered Index is a separate B-tree structure whose leaf nodes contain row locators/pointers.",
                "B) A table can have up to 16 Clustered Indexes but only 1 Non-Clustered Index.",
                "C) Non-Clustered Indexes store all table columns in memory; Clustered Indexes store on disk.",
                "D) Clustered Indexes are only used for primary keys and cannot be defined on custom columns."
            ],
            "correct_answer": "A",
            "hint": "Can a physical dictionary or telephone book be sorted alphabetically in more than one physical order on disk?",
            "explanation": "Because a Clustered Index dictates the physical layout of rows on disk pages, a table can have only ONE Clustered Index. A Non-Clustered Index is a separate B-tree containing key columns plus a bookmark/pointer (the clustering key or RID) pointing back to the base table row.",
            "difficulty": "Intermediate",
            "topic": "SQL Server & Database Design"
        },
        {
            "question": "What is a 'Covering Index' in SQL Server and why does it drastically improve query performance?",
            "code_snippet": "CREATE NONCLUSTERED INDEX IX_Customer_City \nON Customers(City) \nINCLUDE (FirstName, LastName, Email);",
            "options": [
                "A) The index contains all columns requested by the SELECT query, completely eliminating expensive Key/RID Lookups to the base table.",
                "B) It automatically compresses the data into an in-memory columnstore format.",
                "C) It prevents deadlocks by locking all rows in the table during the query.",
                "D) It allows the query optimizer to bypass the SQL Server transaction log."
            ],
            "correct_answer": "A",
            "hint": "When an index contains the WHERE clause columns but NOT the SELECT columns, SQL Server must jump to the base table for every matching row (Key Lookup). How does INCLUDE help?",
            "explanation": "A covering index contains all the columns evaluated or returned by a query. By appending non-key columns via the `INCLUDE` clause, SQL Server satisfies the entire query directly from the non-clustered index leaf pages, avoiding random I/O Key Lookups to the clustered table.",
            "difficulty": "Intermediate",
            "topic": "SQL Server & Database Design"
        },
        {
            "question": "What is the difference between `UNION` and `UNION ALL` in SQL Server?",
            "code_snippet": "-- Query 1:\nSELECT CustomerID FROM US_Orders\nUNION\nSELECT CustomerID FROM EU_Orders;\n\n-- Query 2:\nSELECT CustomerID FROM US_Orders\nUNION ALL\nSELECT CustomerID FROM EU_Orders;",
            "options": [
                "A) `UNION` performs a sort/distinct operation to eliminate duplicate rows, making it slower; `UNION ALL` concatenates all rows including duplicates with minimal overhead.",
                "B) `UNION` only works on numbers; `UNION ALL` works on strings.",
                "C) `UNION ALL` deletes duplicates on the database server; `UNION` deletes duplicates on the client.",
                "D) `UNION` runs in a transaction; `UNION ALL` does not."
            ],
            "correct_answer": "A",
            "hint": "If you know your datasets are mutually exclusive or you want all occurrences, which operator avoids an expensive sorting step?",
            "explanation": "`UNION` compares all returned rows and performs an internal Sort or Hash Distinct operator to remove duplicates, which can be expensive on large datasets. `UNION ALL` simply stitches the result sets together without deduplication, executing much faster and with lower memory/CPU footprint.",
            "difficulty": "Beginner",
            "topic": "SQL Server & Database Design"
        },
        {
            "question": "What is the difference between the `ROW_NUMBER()`, `RANK()`, and `DENSE_RANK()` window functions?",
            "code_snippet": "SELECT Score,\n  ROW_NUMBER() OVER (ORDER BY Score DESC) AS RowNum,\n  RANK() OVER (ORDER BY Score DESC) AS Rnk,\n  DENSE_RANK() OVER (ORDER BY Score DESC) AS DenseRnk\nFROM ExamResults;",
            "options": [
                "A) Given tied scores (e.g. 100, 100, 90): ROW_NUMBER gives 1, 2, 3; RANK gives 1, 1, 3 (skips rank); DENSE_RANK gives 1, 1, 2 (no gaps).",
                "B) ROW_NUMBER is for SQL Server; RANK is for Oracle; DENSE_RANK is for PostgreSQL.",
                "C) RANK requires a PARTITION BY clause; ROW_NUMBER does not.",
                "D) DENSE_RANK produces floating-point percentiles."
            ],
            "correct_answer": "A",
            "hint": "Think about Olympic medals: if two athletes tie for gold (Rank 1, 1), does the next athlete get Silver or Bronze (Rank 2 or 3)?",
            "explanation": "`ROW_NUMBER()` always produces unique sequential integers (1, 2, 3...) regardless of ties. `RANK()` assigns identical ranks to tied rows, but skips subsequent rank numbers to account for the count of ties (1, 1, 3). `DENSE_RANK()` assigns identical ranks to tied rows without leaving gaps in the sequence (1, 1, 2).",
            "difficulty": "Intermediate",
            "topic": "SQL Server & Database Design"
        },
        {
            "question": "In SQL Server transactions, what problem does the `READ COMMITTED SNAPSHOT ISOLATION (RCSI)` level solve?",
            "code_snippet": "ALTER DATABASE SalesDB SET READ_COMMITTED_SNAPSHOT ON;",
            "options": [
                "A) Readers do not block writers and writers do not block readers; readers view a row version from `tempdb` of data committed prior to the start of the query.",
                "B) It disables the transaction log, allowing instant inserts.",
                "C) It prevents data from ever being rolled back in the event of a system crash.",
                "D) It converts the SQL database into a read-only archive."
            ],
            "correct_answer": "A",
            "hint": "In default SQL Server READ COMMITTED, a SELECT statement places shared locks on rows/pages, which blocks concurrent UPDATE statements on those same rows.",
            "explanation": "Default READ COMMITTED uses pessimistic locking: queries acquire shared locks that wait on exclusive write locks. RCSI introduces optimistic row versioning: when a row is updated, SQL Server stores a snapshot of the pre-update row in `tempdb`. Concurrent SELECT queries read the versioned snapshot without waiting for the transaction to commit, eliminating blocking while avoiding dirty reads.",
            "difficulty": "Harder",
            "topic": "SQL Server & Database Design"
        },
        {
            "question": "What is parameter sniffing in SQL Server and when does it become an issue?",
            "code_snippet": "CREATE PROCEDURE GetOrdersByStatus @Status VARCHAR(20)\nAS\nBEGIN\n    SELECT * FROM Orders WHERE Status = @Status;\nEND",
            "options": [
                "A) SQL Server creates and caches an execution plan optimized for the specific parameter passed on the FIRST run, which may be catastrophically suboptimal for subsequent runs with skewed data distribution.",
                "B) A security vulnerability where attackers eavesdrop on plaintext parameter values across network packets.",
                "C) An automatic feature that validates data types before query execution.",
                "D) A tool inside SQL Server Profiler for debugging memory leaks."
            ],
            "correct_answer": "A",
            "hint": "Suppose 99% of orders have Status = 'COMPLETED' (favoring a Clustered Index Scan) and 0.01% have Status = 'NEW' (favoring an Index Seek). What happens if the proc is first called with 'NEW'?",
            "explanation": "When a stored procedure runs for the first time, SQL Server inspects ('sniffs') the passed parameter and generates an execution plan based on its histogram stats. If that plan is cached and reused for parameter values with vastly different data selectivity, it can cause severe performance degradation. Common solutions include `OPTION (RECOMPILE)` or local variable masking.",
            "difficulty": "Harder",
            "topic": "SQL Server & Database Design"
        },
        {
            "question": "What is the difference between `DELETE`, `TRUNCATE`, and `DROP` in SQL Server?",
            "code_snippet": "DELETE FROM AuditLogs;\nTRUNCATE TABLE AuditLogs;\nDROP TABLE AuditLogs;",
            "options": [
                "A) `DELETE` is a DML statement that logs row-by-row and fires triggers; `TRUNCATE` is DDL that deallocates data pages with minimal logging and resets identity; `DROP` removes the entire table schema and data.",
                "B) `TRUNCATE` cannot be rolled back inside a transaction; `DELETE` can.",
                "C) `DELETE` removes table columns; `TRUNCATE` removes table constraints.",
                "D) `TRUNCATE` takes longer than `DELETE` on large tables."
            ],
            "correct_answer": "A",
            "hint": "Note that both `DELETE` and `TRUNCATE` CAN be rolled back if executed inside an active `BEGIN TRANSACTION`! The key difference is how they interact with transaction logs, triggers, and identity columns.",
            "explanation": "`DELETE` removes rows individually, logging each deletion in the transaction log and firing DELETE triggers. `TRUNCATE TABLE` deallocates whole data pages, logs page deallocations (not individual rows), does not fire triggers, resets identity seed, and executes almost instantaneously. Both can be rolled back if wrapped in a transaction. `DROP` permanently removes the table definition from the database schema.",
            "difficulty": "Beginner",
            "topic": "SQL Server & Database Design"
        },
        {
            "question": "What is a Deadlock in SQL Server and how does the engine resolve it?",
            "code_snippet": "-- Session 1 holds Lock A, wants Lock B\n-- Session 2 holds Lock B, wants Lock A",
            "options": [
                "A) A circular dependency where two or more sessions block each other; SQL Server's Deadlock Monitor detects the cycle and terminates the session with the lowest rollback cost (the deadlock victim).",
                "B) A hardware disk failure that freezes the server until an administrator manually restarts the SQL Service.",
                "C) A query that runs for longer than the configured connection timeout.",
                "D) A situation where two users have the same login credentials."
            ],
            "correct_answer": "A",
            "hint": "SQL Server runs a background thread every few seconds checking for cyclical lock dependencies.",
            "explanation": "A deadlock occurs when two transactions hold exclusive locks on different resources and each attempts to acquire a lock on the other's resource. SQL Server's background Deadlock Monitor thread identifies the cycle, chooses the transaction that is least expensive to roll back as the 'deadlock victim', rolls it back, and returns error 1205 to the victim application.",
            "difficulty": "Intermediate",
            "topic": "SQL Server & Database Design"
        },
        {
            "question": "What is the purpose of the `MERGE` statement in SQL Server?",
            "code_snippet": "MERGE TargetTable AS T\nUSING SourceTable AS S ON T.Id = S.Id\nWHEN MATCHED THEN UPDATE SET T.Val = S.Val\nWHEN NOT MATCHED THEN INSERT (Id, Val) VALUES (S.Id, S.Val);",
            "options": [
                "A) Performs an 'UPSERT' (Insert, Update, or Delete) in a single atomic statement based on matching condition between source and target.",
                "B) Merges two SQL Server database backup files into a single archive.",
                "C) Combines clustered index pages to eliminate index fragmentation.",
                "D) Joins two tables and caches the result in Redis."
            ],
            "correct_answer": "A",
            "hint": "Instead of writing an IF EXISTS (SELECT 1 ...) UPDATE ELSE INSERT, what single T-SQL command handles both branches?",
            "explanation": "`MERGE` synchronizes two tables in one statement by evaluating a join predicate. It allows performing INSERTs for new records, UPDATEs for matching records, and optionally DELETEs for records missing from the source table.",
            "difficulty": "Intermediate",
            "topic": "SQL Server & Database Design"
        },
        {
            "question": "When should you use `VARCHAR` vs `NVARCHAR` in SQL Server?",
            "code_snippet": "CREATE TABLE Users (\n    Username VARCHAR(50),\n    FullName NVARCHAR(50)\n);",
            "options": [
                "A) `NVARCHAR` stores Unicode data (UTF-16) requiring 2 bytes per character; `VARCHAR` stores non-Unicode (ASCII/ANSI) data using 1 byte per character.",
                "B) `NVARCHAR` is faster for numbers; `VARCHAR` is faster for dates.",
                "C) `VARCHAR` supports up to 8000 characters; `NVARCHAR` has no character limits.",
                "D) `NVARCHAR` cannot be indexed; `VARCHAR` can."
            ],
            "correct_answer": "A",
            "hint": "If your application needs to support international languages, accents, Hindi, Japanese, or emojis, which data type is required?",
            "explanation": "`VARCHAR` uses 1 byte per character and is suitable for standard ASCII/single-byte character sets. `NVARCHAR` stores 2 bytes per character in UTF-16 (or variable in UTF-8 collations), allowing multilingual support, international scripts, and special symbols at the cost of double the storage space.",
            "difficulty": "Beginner",
            "topic": "SQL Server & Database Design"
        }
    ],

    "System Architecture": [
        {
            "question": "In RESTful API design, what is the definition and importance of 'Idempotency'?",
            "code_snippet": "// HTTP Methods:\nGET, PUT, DELETE, POST, PATCH",
            "options": [
                "A) An operation that produces the exact same server state whether executed once or multiple times consecutively (e.g. GET, PUT, DELETE).",
                "B) An API endpoint that never requires authentication or API keys.",
                "C) An endpoint that runs synchronously in less than 50 milliseconds.",
                "D) An operation that never writes to a relational database."
            ],
            "correct_answer": "A",
            "hint": "If a network glitch causes a client to resend a PUT or DELETE request, does the server end up in a corrupt state or duplicate records?",
            "explanation": "An HTTP method is idempotent if repeating identical requests has the same effect on the server state as a single request. `PUT` (replace resource) and `DELETE` (delete resource) are idempotent. `POST` is NOT idempotent because resending a POST /orders request will typically create multiple duplicate orders.",
            "difficulty": "Intermediate",
            "topic": "System Architecture & Problem Solving"
        },
        {
            "question": "What is the 'N+1 Query Problem' in ORMs (like Entity Framework or Hibernate) and how do you resolve it?",
            "code_snippet": "// Problematic code:\nvar orders = await dbContext.Orders.ToListAsync();\nforeach(var order in orders)\n{\n    // Triggers individual query per iteration!\n    var customer = order.Customer.Name;\n}",
            "options": [
                "A) 1 initial query fetches N orders, then N subsequent queries fetch each customer; resolved via Eager Loading using `.Include(o => o.Customer)`.",
                "B) A database deadlocks when N users query at the same second; resolved by adding more CPU cores.",
                "C) SQL Server limits queries to N+1 joins; resolved by splitting into multiple tables.",
                "D) It occurs when a table has more than N+1 indexes; resolved by dropping indexes."
            ],
            "correct_answer": "A",
            "hint": "If you have 100 orders, lazy loading executes 1 query to get the orders and 100 separate round trips to the database to get each customer (101 queries total).",
            "explanation": "The N+1 problem occurs with lazy loading when iterating over a parent collection and accessing a child navigation property. Instead of one single SQL JOIN, the application issues 1 initial query plus N queries for each parent item, causing severe network latency and DB load. Using `.Include()` (Eager Loading) or projection (`.Select()`) joins the data in a single SQL query.",
            "difficulty": "Intermediate",
            "topic": "System Architecture & Problem Solving"
        },
        {
            "question": "What does the Single Responsibility Principle (SRP) in SOLID mean in practice?",
            "code_snippet": "// Violates SRP:\npublic class InvoiceService\n{\n    public void CalculateTotal() { ... }\n    public void SaveToDatabase() { ... }\n    public void SendEmailNotification() { ... }\n    public void GeneratePdfReport() { ... }\n}",
            "options": [
                "A) A class should have only one reason to change, meaning it should encapsulate only one responsibility or business actor concern.",
                "B) A class can have only one public method and no private helper methods.",
                "C) A software solution should have only one database context.",
                "D) A developer can work on only one task at a time."
            ],
            "correct_answer": "A",
            "hint": "If email template formatting changes, or the database connection changes, or tax calculation rules change, should the same class be modified?",
            "explanation": "As formulated by Robert C. Martin, 'A class should have one, and only one, reason to change.' In the snippet, InvoiceService handles financial calculation, database persistence, email communication, and PDF rendering. Changes to email or PDF generation risk breaking core invoice calculations. Splitting them into `InvoiceCalculator`, `InvoiceRepository`, and `NotificationService` adheres to SRP.",
            "difficulty": "Beginner",
            "topic": "System Architecture & Problem Solving"
        },
        {
            "question": "What is the primary difference between Horizontal Scaling (Scaling Out) and Vertical Scaling (Scaling Up)?",
            "code_snippet": "// Scenario A: Upgrading server from 16GB RAM to 128GB RAM\n// Scenario B: Adding 5 additional load-balanced server instances",
            "options": [
                "A) Vertical scaling adds more resources (CPU/RAM) to a single machine; Horizontal scaling adds more machine nodes to a distributed pool.",
                "B) Horizontal scaling is for databases only; Vertical scaling is for web servers only.",
                "C) Vertical scaling guarantees 100% uptime with no single point of failure.",
                "D) Horizontal scaling requires all servers to be in the same physical rack."
            ],
            "correct_answer": "A",
            "hint": "Which approach eventually hits physical hardware limits and cost boundaries, and which approach provides redundancy against server crashes?",
            "explanation": "Scaling Up (Vertical) increases computing capacity of an existing server. It has a hard hardware ceiling and retains a single point of failure. Scaling Out (Horizontal) adds more instances behind a load balancer, providing high availability, elastic elasticity, and fault tolerance at the cost of distributed systems complexity.",
            "difficulty": "Beginner",
            "topic": "System Architecture & Problem Solving"
        }
    ]
}

# Curated practical coding challenges
CODING_QUESTIONS = [
    {
        "type": "coding",
        "topic": "Practical Coding: .NET / C#",
        "title": "Thread-Safe In-Memory Cache with TTL Expiration",
        "question": "Implement an asynchronous, thread-safe memory cache in C# that supports item expiration (TTL). The cache must safely allow concurrent reads and writes without throwing collection-modified exceptions.",
        "difficulty": "Intermediate",
        "starter_code": """using System;
using System.Collections.Concurrent;
using System.Threading.Tasks;

public class InMemoryCache<TKey, TValue>
{
    private readonly ConcurrentDictionary<TKey, (TValue Value, DateTime Expiry)> _storage = new();

    public void Set(TKey key, TValue value, TimeSpan ttl)
    {
        // TODO: Store value with absolute expiry time (DateTime.UtcNow + ttl)
    }

    public bool TryGet(TKey key, out TValue value)
    {
        // TODO: Retrieve value. If expired, remove from storage and return false.
        value = default;
        return false;
    }
}""",
        "solution_code": """using System;
using System.Collections.Concurrent;

public class InMemoryCache<TKey, TValue>
{
    private readonly ConcurrentDictionary<TKey, (TValue Value, DateTime Expiry)> _storage = new();

    public void Set(TKey key, TValue value, TimeSpan ttl)
    {
        var expiry = DateTime.UtcNow.Add(ttl);
        _storage[key] = (value, expiry);
    }

    public bool TryGet(TKey key, out TValue value)
    {
        if (_storage.TryGetValue(key, out var entry))
        {
            if (DateTime.UtcNow <= entry.Expiry)
            {
                value = entry.Value;
                return true;
            }
            // Lazy eviction of expired entry
            _storage.TryRemove(key, out _);
        }
        value = default;
        return false;
    }
}""",
        "public_test_cases": [
            {"name": "Public Test 1 [Valid TTL Retrieval]", "input": "Set('user_1', 'John', 60s) -> TryGet('user_1')", "expected": "Returns true with value 'John'", "explanation": "Basic retrieval within valid TTL window."},
            {"name": "Public Test 2 [Expired TTL Eviction]", "input": "Set('temp_token', 'xyz', -1s) -> TryGet('temp_token')", "expected": "Returns false and auto-evicts expired token", "explanation": "Lazy eviction cleans up stale entry on read."}
        ],
        "hidden_test_cases": [
            {"name": "Hidden Test 1 [Null / Default Key Boundary]", "input": "TryGet(null, out _)", "expected": "Defensive handling: returns false or throws ArgumentNullException gracefully", "explanation": "Edge case: null key handling without memory corruption."},
            {"name": "Hidden Test 2 [Overwrite Key & Refresh TTL]", "input": "Set('key1', 'val1', 5s) -> Set('key1', 'val2', 120s) -> TryGet('key1')", "expected": "Returns true with 'val2' and updated expiry", "explanation": "Overwrites prior value and extends TTL."},
            {"name": "Hidden Test 3 [Concurrent Race Conditions]", "input": "1,000 parallel threads reading and writing simultaneously", "expected": "Zero deadlocks, zero InvalidOperationException", "explanation": "Stress test: thread safety under heavy contention."}
        ],
        "test_cases": [
            {"input": "Set('user_1', 'John', 60s) -> TryGet('user_1')", "expected": "Returns true with value 'John'"},
            {"input": "Set('temp_token', 'xyz', -1s) -> TryGet('temp_token')", "expected": "Returns false and auto-evicts expired token"}
        ],
        "hint": "Use ConcurrentDictionary and compare DateTime.UtcNow against the stored expiry date. Evict lazily on read if expired.",
        "explanation": "ConcurrentDictionary provides lock-free or fine-grained lock operations for high throughput. Adding lazy eviction on access prevents memory leaks of expired tokens without requiring a constant polling background thread."
    },
    {
        "type": "coding",
        "topic": "Practical Coding: Angular & RxJS",
        "title": "Type-Ahead Search Observable with SwitchMap & Debounce",
        "question": "Construct an RxJS reactive search pipeline in Angular/TypeScript that takes keystroke inputs, prevents duplicate API queries, debounces user typing by 300ms, and cancels older pending HTTP requests when new characters arrive.",
        "difficulty": "Intermediate",
        "starter_code": """import { Observable, of } from 'rxjs';
import { debounceTime, distinctUntilChanged, switchMap, catchError } from 'rxjs/operators';

export function createSearchStream(
  searchTerm$: Observable<string>,
  apiService: (query: string) => Observable<string[]>
): Observable<string[]> {
  // TODO: Build pipeline using debounceTime, distinctUntilChanged, switchMap, and catchError
  return searchTerm$.pipe(
    // your operators here
  );
}""",
        "solution_code": """import { Observable, of } from 'rxjs';
import { debounceTime, distinctUntilChanged, switchMap, catchError } from 'rxjs/operators';

export function createSearchStream(
  searchTerm$: Observable<string>,
  apiService: (query: string) => Observable<string[]>
): Observable<string[]> {
  return searchTerm$.pipe(
    debounceTime(300),
    distinctUntilChanged(),
    switchMap(term => {
      if (!term.trim()) {
        return of([]);
      }
      return apiService(term).pipe(
        catchError(err => {
          console.error('Search API failure:', err);
          return of([]);
        })
      );
    })
  );
}""",
        "public_test_cases": [
            {"name": "Public Test 1 [Typing Debounce]", "input": "User types 'a', 'an', 'ang' within 100ms", "expected": "Debounces until typing stops; only 1 API call for 'ang'", "explanation": "debounceTime suppresses intermediate network spam."},
            {"name": "Public Test 2 [Duplicate Query Suppression]", "input": "User enters duplicate string or backs up and retypes same word", "expected": "distinctUntilChanged suppresses duplicate dispatch", "explanation": "Suppresses duplicate API calls for identical values."}
        ],
        "hidden_test_cases": [
            {"name": "Hidden Test 1 [Whitespace / Empty Term]", "input": "User inputs '   ' (spaces) or clears the input box", "expected": "Returns of([]) immediately without firing API request", "explanation": "Edge case: empty string handling prevents wasteful requests."},
            {"name": "Hidden Test 2 [Race Condition / Out-of-Order Cancellation]", "input": "Query 1 takes 500ms, Query 2 arrives at 350ms and takes 100ms", "expected": "switchMap cancels Query 1; only Query 2 result emits", "explanation": "Race condition prevention: older responses are discarded."},
            {"name": "Hidden Test 3 [Stream Resilience on 500 Error]", "input": "API throws 500 Internal Server Error", "expected": "catchError inside switchMap catches error and returns of([]); stream does not die", "explanation": "Resilience: outer stream remains active for future keystrokes."}
        ],
        "test_cases": [
            {"input": "User types 'a', 'an', 'ang' within 100ms", "expected": "Debounces until typing stops; only 1 API call for 'ang'"},
            {"input": "User enters duplicate string or backs up and retypes same word", "expected": "distinctUntilChanged suppresses duplicate dispatch"}
        ],
        "hint": "switchMap automatically cancels the in-flight inner observable if a new value is emitted by the source stream.",
        "explanation": "debounceTime(300) waits for user pause; distinctUntilChanged prevents duplicate queries; switchMap ensures race conditions are eliminated by abandoning prior in-flight network requests."
    },
    {
        "type": "coding",
        "topic": "Practical Coding: SQL Server",
        "title": "Find Top 2 Highest Salaries per Department with Ties",
        "question": "Write a T-SQL query that finds the top 2 highest paid employees in each department. If two employees share the same salary, they should share the same rank without skipping numbers.",
        "difficulty": "Intermediate",
        "starter_code": """-- Given Tables:
-- Employees (Id INT, Name NVARCHAR(100), Salary DECIMAL(18,2), DepartmentId INT)
-- Departments (Id INT, DepartmentName NVARCHAR(100))

WITH RankedEmployees AS (
    -- TODO: Use DENSE_RANK() OVER (PARTITION BY DepartmentId ORDER BY Salary DESC)
)
SELECT 
    -- TODO: Join with Departments and filter top 2
;""",
        "solution_code": """WITH RankedEmployees AS (
    SELECT 
        e.Id,
        e.Name AS EmployeeName,
        e.Salary,
        d.DepartmentName,
        DENSE_RANK() OVER (PARTITION BY e.DepartmentId ORDER BY e.Salary DESC) AS SalaryRank
    FROM Employees e
    INNER JOIN Departments d ON e.DepartmentId = d.Id
)
SELECT 
    DepartmentName,
    EmployeeName,
    Salary,
    SalaryRank
FROM RankedEmployees
WHERE SalaryRank <= 2
ORDER BY DepartmentName, SalaryRank, EmployeeName;""",
        "public_test_cases": [
            {"name": "Public Test 1 [Tied Salaries in Department]", "input": "Department IT with salaries: $120k, $120k, $100k, $90k", "expected": "Rank 1: both $120k; Rank 2: $100k (DENSE_RANK preserves consecutive tiers)", "explanation": "DENSE_RANK ensures tied salaries share Rank 1 and next tier is Rank 2."},
            {"name": "Public Test 2 [Distinct Consecutive Tiers]", "input": "Department HR with salaries: $80k, $70k, $60k", "expected": "Rank 1: $80k, Rank 2: $70k", "explanation": "Standard top 2 selection across partitions."}
        ],
        "hidden_test_cases": [
            {"name": "Hidden Test 1 [Single Employee Partition]", "input": "Department Legal containing only 1 employee with salary $150k", "expected": "Returns exactly 1 record without error", "explanation": "Boundary case: sparse department partitions."},
            {"name": "Hidden Test 2 [Multiple Ties at Rank 2 Boundary]", "input": "Department Sales: $110k, $95k, $95k, $95k, $80k", "expected": "Returns $110k (Rank 1) and all 3 $95k records (Rank 2)", "explanation": "Edge case: all tied employees at Rank 2 must be returned."},
            {"name": "Hidden Test 3 [NULL Department Handling]", "input": "Employees with NULL DepartmentId", "expected": "Handled cleanly via INNER JOIN without syntax errors", "explanation": "Integrity check: unassigned relations."}
        ],
        "test_cases": [
            {"input": "Department IT with salaries: $120k, $120k, $100k, $90k", "expected": "Rank 1: both $120k; Rank 2: $100k (DENSE_RANK preserves consecutive tiers)"}
        ],
        "hint": "Use DENSE_RANK() rather than ROW_NUMBER(). ROW_NUMBER assigns arbitrary ordering for ties, whereas DENSE_RANK ranks tied salaries equally without gaps.",
        "explanation": "DENSE_RANK() partitions the data by department and assigns ranks based on descending salary. It ensures tied salaries receive the identical rank and the subsequent salary receives the next sequential integer."
    }
]

# Curated behavioral & hiring fit questions
BEHAVIORAL_QUESTIONS = [
    {
        "type": "behavioral",
        "topic": "Hiring & Behavioral Fit",
        "title": "Why Should We Hire You For This Engineering Role?",
        "question": "Why should our team hire you for this role over other qualified developers with similar technical backgrounds?",
        "difficulty": "All Levels",
        "star_framework_prompt": "Structure your pitch: 1) Your unique dual-strength combination (.NET backend + Angular frontend + SQL), 2) Proven ownership & reduction of handoff friction, 3) Real business impact (e.g. latency reduction, reliable delivery).",
        "key_lookouts": "Demonstrates clear self-awareness, alignment with product goals, cross-functional empathy, and quantifiable impact rather than generic clichés.",
        "sample_strong_answer": "You should hire me because I bridge the gap between high-throughput backend architecture (.NET Core / SQL Server) and responsive frontend state management (Angular). Rather than waiting on tickets between separate teams, I take full ownership from database indexing down to client UX. In my recent projects, this full-lifecycle perspective allowed me to eliminate redundant payload transformations, cutting API latency by over 30% and speeding up feature delivery cycles. I bring proactive communication, clean architectural rigor, and a strong drive to make both the product and my teammates succeed.",
        "hint": "Avoid generic statements like 'I am hardworking'. Connect your specific technical stack to business efficiency and developer collaboration."
    },
    {
        "type": "behavioral",
        "topic": "Hiring & Behavioral Fit",
        "title": "Critical Production Incident / High-Pressure Diagnosis",
        "question": "Tell me about a time you encountered a severe production bug, latency spike, or outage under a tight deadline. How did you diagnose it, prioritize remediation, and prevent recurrence?",
        "difficulty": "All Levels",
        "star_framework_prompt": "Follow the STAR method: Situation (what broke and the customer impact), Task (your immediate responsibility), Action (the diagnostic tools and fix you applied), Result (uptime restored and post-mortem safeguards).",
        "key_lookouts": "Calm under pressure, systematic root cause analysis (metrics/logs rather than guessing), post-incident prevention (unit tests, alerts, health checks).",
        "sample_strong_answer": "Situation: During a high-traffic release, our payment processing API response times degraded from 180ms to over 6 seconds, risking order drop-offs. Task: As on-call engineer, I was responsible for identifying the bottleneck and restoring normal SLAs immediately. Action: Rather than restarting servers blindly, I inspected SQL Server Active Monitor and application logs, discovering an unindexed foreign key column causing table scans during concurrent transactions. I deployed an emergency covering non-clustered index on the foreign key and enabled connection pooling tweaks. Result: Response times dropped back to 140ms within 15 minutes, with zero lost transactions. As a post-mortem action, I added automated EF Core migration linters and index checks to our CI/CD pipeline to prevent unindexed relations in future releases.",
        "hint": "Focus on root cause analysis tools (profilers, telemetry) and emphasize the systemic fix so the error never happens again."
    },
    {
        "type": "behavioral",
        "topic": "Hiring & Behavioral Fit",
        "title": "Handling Disagreements in Technical Design or Code Reviews",
        "question": "Describe a scenario where you disagreed with a senior developer, tech lead, or product manager on an architectural decision or code review. How did you navigate the conversation to reach an optimal outcome?",
        "difficulty": "All Levels",
        "star_framework_prompt": "STAR: Situation (the debate between Approach A vs B), Task (your goal to achieve the best engineering decision respectfully), Action (benchmarks, proof-of-concept, objective criteria), Result (consensus reached, project delivered).",
        "key_lookouts": "Disagree and commit principle, relying on objective data/benchmarks rather than ego, respecting timeline constraints, and fostering high psychological safety.",
        "sample_strong_answer": "In a previous project, a senior engineer proposed using distributed Redis caching for every lookup table, while I was concerned about the operational overhead and cache invalidation complexity for rarely changing reference data. Instead of arguing opinion, I built a quick 30-minute benchmark comparing an in-memory IMemoryCache with Redis for our specific access pattern, demonstrating that local in-memory caching gave us sub-millisecond reads with zero network latency. We reviewed the numbers together, agreed to use local memory caching for reference data and reserved Redis exclusively for shared session state. The outcome was simpler code, reduced cloud infrastructure costs, and a strengthened working relationship with my peer.",
        "hint": "Always rely on data, prototypes, and team consensus rather than asserting that you were simply 'right'."
    }
]


def get_curated_questions(
    primary_skill: str,
    secondary_skill: str,
    years_of_experience: float,
    difficulty: str,
    target_count: int = 15,
    include_coding: bool = True,
    include_behavioral: bool = True
) -> List[Dict[str, Any]]:
    """
    Selects and balances authentic interview questions matching candidate profile.
    Dynamically balances Technical MCQs, Hands-on Coding Challenges, and Behavioral/Hiring questions.
    """
    selected: List[Dict[str, Any]] = []
    
    # 1. Determine quota breakdown
    coding_count = 0
    behavioral_count = 0
    
    if include_coding:
        coding_count = 1 if target_count <= 10 else (2 if target_count <= 20 else 3)
    if include_behavioral:
        behavioral_count = 1 if target_count <= 15 else 2
        
    mcq_target = max(1, target_count - (coding_count + behavioral_count))
    
    # 2. Gather MCQs
    pool_dotnet = list(QUESTIONS_DATA[".NET"])
    pool_angular = list(QUESTIONS_DATA["Angular"])
    pool_sql = list(QUESTIONS_DATA["SQL Server"])
    pool_arch = list(QUESTIONS_DATA["System Architecture"])
    
    random.shuffle(pool_dotnet)
    random.shuffle(pool_angular)
    random.shuffle(pool_sql)
    random.shuffle(pool_arch)
    
    count_p = min(len(pool_dotnet), int(mcq_target * 0.35))
    count_s = min(len(pool_angular), int(mcq_target * 0.35))
    count_sql = min(len(pool_sql), int(mcq_target * 0.20))
    count_arch = max(0, mcq_target - (count_p + count_s + count_sql))
    
    mcq_selected = []
    mcq_selected.extend(pool_dotnet[:count_p])
    mcq_selected.extend(pool_angular[:count_s])
    mcq_selected.extend(pool_sql[:count_sql])
    mcq_selected.extend(pool_arch[:count_arch])
    
    for q in mcq_selected:
        item = dict(q)
        item["type"] = "mcq"
        selected.append(item)
        
    # 3. Add Coding Challenges
    if coding_count > 0:
        c_pool = list(CODING_QUESTIONS)
        random.shuffle(c_pool)
        for c in c_pool[:coding_count]:
            selected.append(dict(c))
            
    # 4. Add Behavioral Questions
    if behavioral_count > 0:
        b_pool = list(BEHAVIORAL_QUESTIONS)
        random.shuffle(b_pool)
        for b in b_pool[:behavioral_count]:
            selected.append(dict(b))
            
    # 5. Format & Number sequentially
    final_questions = []
    for idx, q in enumerate(selected, 1):
        item = dict(q)
        item["id"] = idx
        if "type" not in item:
            item["type"] = "mcq"
        if difficulty in ["Beginner", "Intermediate", "Harder"]:
            item["difficulty"] = difficulty
        final_questions.append(item)
        
    return final_questions

